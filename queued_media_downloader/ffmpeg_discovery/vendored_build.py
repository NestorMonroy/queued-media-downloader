"""Comprobación de la build de ffmpeg incluida en vendor/ (ADR-0005, ADR-0018)."""

import re
from pathlib import Path

from queued_media_downloader.ffmpeg_discovery.checksum_cache import ChecksumCache
from queued_media_downloader.ffmpeg_discovery.ffmpeg_locator import (
    FfmpegUnavailableError,
)

SOURCE_FILE_NAME = "SOURCE.md"
# Fila de la tabla de SOURCE.md: | `avcodec-63.dll` | `<sha256>` |
CHECKSUM_ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", re.MULTILINE)
# Un clon sin Git LFS deja en lugar de cada binario un texto de ~130 bytes.
GIT_LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/"
GIT_LFS_POINTER_MAX_BYTES = 1024
RESTORE_HINT = (
    "Run 'git lfs pull' in the project folder, or set ffmpeg_path to your own ffmpeg."
)


def recorded_checksums(build_directory: Path) -> dict[str, str]:
    """SHA-256 de cada archivo de bin/ según SOURCE.md; vacío si no hay build."""
    source_file = build_directory / SOURCE_FILE_NAME
    if not source_file.is_file():
        return {}
    source_text = source_file.read_text(encoding="utf-8")
    return dict(CHECKSUM_ROW.findall(source_text))


def verify_vendored_build(
    build_directory: Path,
    expected_checksums: dict[str, str],
    checksum_cache: ChecksumCache,
) -> None:
    """Comprueba que cada archivo registrado existe, es real y no cambió.

    Raises:
        FfmpegUnavailableError: Con el primer archivo que falta, es un puntero
            de Git LFS o no coincide con su SHA-256.
    """
    bin_directory = build_directory / "bin"
    for file_name, expected_sha256 in sorted(expected_checksums.items()):
        _verify_file(bin_directory / file_name, expected_sha256, checksum_cache)


def _verify_file(
    path: Path, expected_sha256: str, checksum_cache: ChecksumCache
) -> None:
    """Falla con un mensaje que nombra el archivo y cómo restaurarlo."""
    if not path.is_file():
        message = f"{path.name} is missing from {path.parent}. {RESTORE_HINT}"
        raise FfmpegUnavailableError(message)
    if _is_git_lfs_pointer(path):
        message = (
            f"{path.name} in {path.parent} is a Git LFS pointer, not the real "
            f"file: the project was cloned without Git LFS. {RESTORE_HINT}"
        )
        raise FfmpegUnavailableError(message)
    if checksum_cache.sha256_of(path) != expected_sha256:
        message = (
            f"{path.name} in {path.parent} does not match its SHA-256 in "
            f"{SOURCE_FILE_NAME}: the file is damaged or was replaced. Restore it "
            "with 'git checkout -- vendor/ffmpeg', or set ffmpeg_path to your "
            "own ffmpeg."
        )
        raise FfmpegUnavailableError(message)


def _is_git_lfs_pointer(path: Path) -> bool:
    """Un archivo pequeño que empieza como un puntero de Git LFS."""
    if path.stat().st_size > GIT_LFS_POINTER_MAX_BYTES:
        return False
    with path.open("rb") as file:
        return file.read(len(GIT_LFS_POINTER_PREFIX)) == GIT_LFS_POINTER_PREFIX
