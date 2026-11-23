"""Build de ffmpeg incluida en vendor/ (ADR-0005, ADR-0018)."""

import subprocess
from pathlib import Path

import pytest

from queued_media_downloader.configuration import project_root
from queued_media_downloader.ffmpeg_discovery import FfmpegSource
from queued_media_downloader.ffmpeg_discovery.checksum_cache import ChecksumCache
from queued_media_downloader.ffmpeg_discovery.file_system_ffmpeg_locator import (
    VENDORED_BUILD_NAME,
    FileSystemFfmpegLocator,
)
from queued_media_downloader.ffmpeg_discovery.vendored_build import (
    recorded_checksums,
    verify_vendored_build,
)

BUILD_VERSION = "n9.0.2-39-g7adfbe40dc"
BUILD_DIRECTORY = (
    project_root() / "vendor" / "ffmpeg" / f"{BUILD_VERSION}-win64-lgpl-shared"
)
EXPECTED_BINARIES = {
    "ffmpeg.exe",
    "ffprobe.exe",
    "avcodec-63.dll",
    "avdevice-63.dll",
    "avfilter-12.dll",
    "avformat-63.dll",
    "avutil-61.dll",
    "swresample-7.dll",
    "swscale-10.dll",
}
ZIP_SHA256 = "e907b01fa4783913151237e37df2a10fa97d99a1598a021bf59d4ae62ffed4c0"
# Primeros bytes de un puntero de Git LFS: el binario no se descargó.
GIT_LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/"


def test_build_contains_ffmpeg_ffprobe_and_their_libraries_without_ffplay() -> None:
    binaries = {path.name for path in (BUILD_DIRECTORY / "bin").iterdir()}

    assert binaries == EXPECTED_BINARIES


def test_build_contains_only_bin_license_and_source() -> None:
    entries = {path.name for path in BUILD_DIRECTORY.iterdir()}

    assert entries == {"bin", "LICENSE.txt", "SOURCE.md"}


def test_license_is_the_lgpl_of_the_build() -> None:
    license_text = (BUILD_DIRECTORY / "LICENSE.txt").read_text(encoding="utf-8")

    assert "GNU LESSER GENERAL PUBLIC LICENSE" in license_text
    assert "Version 3" in license_text


def test_source_records_the_dated_url_the_checksum_and_the_source_code() -> None:
    source = (BUILD_DIRECTORY / "SOURCE.md").read_text(encoding="utf-8")

    assert "/releases/download/autobuild-2026-10-31-12-59/" in source
    assert ZIP_SHA256 in source
    assert "https://github.com/FFmpeg/FFmpeg/tree/7adfbe40dc" in source


def test_license_and_source_are_plain_text_outside_git_lfs() -> None:
    for name in ("LICENSE.txt", "SOURCE.md"):
        content = (BUILD_DIRECTORY / name).read_bytes()

        assert not content.startswith(GIT_LFS_POINTER_PREFIX), name


def test_locator_pins_this_build() -> None:
    assert BUILD_DIRECTORY.name == VENDORED_BUILD_NAME


def test_every_binary_matches_its_checksum_in_source_md(tmp_path: Path) -> None:
    checksums = recorded_checksums(BUILD_DIRECTORY)

    assert set(checksums) == EXPECTED_BINARIES
    verify_vendored_build(
        BUILD_DIRECTORY, checksums, ChecksumCache(tmp_path / "checksums.json")
    )


@pytest.mark.windows
@pytest.mark.parametrize("program_name", ["ffmpeg.exe", "ffprobe.exe"])
def test_vendored_program_starts_and_reports_its_version(program_name: str) -> None:
    completed_process = subprocess.run(
        [str(BUILD_DIRECTORY / "bin" / program_name), "-version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed_process.returncode == 0, completed_process.stderr
    program = program_name.removesuffix(".exe")
    assert completed_process.stdout.startswith(f"{program} version {BUILD_VERSION}")


@pytest.mark.windows
def test_locator_uses_the_vendored_build_when_nothing_is_configured(
    tmp_path: Path,
) -> None:
    installation = FileSystemFfmpegLocator(
        configured_path=None,
        vendored_build_directory=BUILD_DIRECTORY,
        verification_cache_file=tmp_path / "ffmpeg-verification.json",
    ).locate()

    assert installation.source is FfmpegSource.VENDORED
    assert installation.ffmpeg_version.startswith(f"ffmpeg version {BUILD_VERSION}")
