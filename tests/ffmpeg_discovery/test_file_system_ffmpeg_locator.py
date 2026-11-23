import hashlib
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from queued_media_downloader.ffmpeg_discovery import (
    FfmpegInstallation,
    FfmpegSource,
    FfmpegUnavailableError,
)
from queued_media_downloader.ffmpeg_discovery.file_system_ffmpeg_locator import (
    FileSystemFfmpegLocator,
    read_program_version,
)

FFMPEG_CONTENT = b"MZ fake ffmpeg"
FFPROBE_CONTENT = b"MZ fake ffprobe"
DLL_CONTENT = b"MZ fake library"
GIT_LFS_POINTER = (
    b"version https://git-lfs.github.com/spec/v1\n"
    b"oid sha256:ac68fc6b9c30b7378b54afccc7e9eff84b318ba1e876d9ab85c8b8cc1dd7e4ea\n"
    b"size 551424\n"
)


class FakeVersionReader:
    """Devuelve una versión por programa y registra a quién se consultó."""

    def __init__(self, failing_program: str | None = None) -> None:
        """failing_program no responde a -version."""
        self._failing_program = failing_program
        self.read_paths: list[Path] = []

    def __call__(self, program_path: Path) -> str:
        """Primera línea de -version, como el programa real."""
        self.read_paths.append(program_path)
        program = program_path.stem
        if program == self._failing_program:
            message = f"{program_path} did not answer -version"
            raise OSError(message)
        return f"{program} version test-build"


def write_build(
    build_directory: Path,
    files: Mapping[str, bytes],
    recorded_checksums: Mapping[str, bytes] | None = None,
) -> Path:
    """Crea una build ficticia con su SOURCE.md; devuelve la carpeta bin/.

    recorded_checksums permite registrar en SOURCE.md un contenido distinto
    del escrito, para simular un binario corrupto.
    """
    bin_directory = build_directory / "bin"
    bin_directory.mkdir(parents=True)
    for name, content in files.items():
        (bin_directory / name).write_bytes(content)
    rows = "\n".join(
        f"| `{name}` | `{hashlib.sha256(content).hexdigest()}` |"
        for name, content in (recorded_checksums or files).items()
    )
    (build_directory / "SOURCE.md").write_text(
        f"# Origen\n\n| Archivo de `bin/` | SHA-256 |\n|---|---|\n{rows}\n",
        encoding="utf-8",
    )
    return bin_directory


VALID_BUILD_FILES = {
    "ffmpeg.exe": FFMPEG_CONTENT,
    "ffprobe.exe": FFPROBE_CONTENT,
    "avcodec-63.dll": DLL_CONTENT,
}


def make_locator(
    tmp_path: Path,
    *,
    configured_path: Path | None = None,
    version_reader: FakeVersionReader | None = None,
    programs_on_path: Mapping[str, str] | None = None,
) -> FileSystemFfmpegLocator:
    """Localizador con la build en tmp_path/vendor y la caché en tmp_path/state."""
    found_on_path: Callable[[str], str | None] = (programs_on_path or {}).get
    return FileSystemFfmpegLocator(
        configured_path=configured_path,
        vendored_build_directory=tmp_path / "vendor" / "build",
        verification_cache_file=tmp_path / "state" / "ffmpeg-verification.json",
        read_version=version_reader or FakeVersionReader(),
        find_on_path=found_on_path,
        executable_suffix=".exe",
    )


def test_configured_directory_comes_first(tmp_path: Path) -> None:
    write_build(tmp_path / "vendor" / "build", VALID_BUILD_FILES)
    own_directory = tmp_path / "own"
    own_directory.mkdir()
    (own_directory / "ffmpeg.exe").write_bytes(b"own ffmpeg")
    (own_directory / "ffprobe.exe").write_bytes(b"own ffprobe")

    installation = make_locator(tmp_path, configured_path=own_directory).locate()

    assert installation == FfmpegInstallation(
        source=FfmpegSource.CONFIGURED,
        ffmpeg_location=own_directory,
        ffmpeg_version="ffmpeg version test-build",
        ffprobe_version="ffprobe version test-build",
    )


def test_configured_ffmpeg_executable_finds_ffprobe_beside_it(tmp_path: Path) -> None:
    own_directory = tmp_path / "own"
    own_directory.mkdir()
    (own_directory / "ffmpeg.exe").write_bytes(b"own ffmpeg")
    (own_directory / "ffprobe.exe").write_bytes(b"own ffprobe")

    installation = make_locator(
        tmp_path, configured_path=own_directory / "ffmpeg.exe"
    ).locate()

    assert installation.source is FfmpegSource.CONFIGURED
    assert installation.ffmpeg_location == own_directory


def test_configured_path_without_ffprobe_fails_instead_of_falling_back(
    tmp_path: Path,
) -> None:
    write_build(tmp_path / "vendor" / "build", VALID_BUILD_FILES)
    own_directory = tmp_path / "own"
    own_directory.mkdir()
    (own_directory / "ffmpeg.exe").write_bytes(b"own ffmpeg")

    with pytest.raises(FfmpegUnavailableError) as raised:
        make_locator(tmp_path, configured_path=own_directory).locate()

    assert "ffmpeg_path" in str(raised.value)
    assert "ffprobe.exe" in str(raised.value)


def test_vendored_build_is_used_when_nothing_is_configured(tmp_path: Path) -> None:
    bin_directory = write_build(tmp_path / "vendor" / "build", VALID_BUILD_FILES)
    version_reader = FakeVersionReader()

    installation = make_locator(tmp_path, version_reader=version_reader).locate()

    assert installation.source is FfmpegSource.VENDORED
    assert installation.ffmpeg_location == bin_directory
    assert version_reader.read_paths == [
        bin_directory / "ffmpeg.exe",
        bin_directory / "ffprobe.exe",
    ]


@pytest.mark.parametrize("pointer_file", ["ffmpeg.exe", "avcodec-63.dll"])
def test_git_lfs_pointer_asks_for_git_lfs_pull(
    tmp_path: Path, pointer_file: str
) -> None:
    files = {**VALID_BUILD_FILES, pointer_file: GIT_LFS_POINTER}
    write_build(
        tmp_path / "vendor" / "build", files, recorded_checksums=VALID_BUILD_FILES
    )

    with pytest.raises(FfmpegUnavailableError) as raised:
        make_locator(tmp_path).locate()

    message = str(raised.value)
    assert "git lfs pull" in message
    assert "ffmpeg_path" in message
    assert pointer_file in message


def test_binary_that_differs_from_source_md_is_reported_as_corrupt(
    tmp_path: Path,
) -> None:
    files = {**VALID_BUILD_FILES, "avcodec-63.dll": b"MZ damaged library"}
    write_build(
        tmp_path / "vendor" / "build", files, recorded_checksums=VALID_BUILD_FILES
    )

    with pytest.raises(FfmpegUnavailableError) as raised:
        make_locator(tmp_path).locate()

    assert "avcodec-63.dll" in str(raised.value)
    assert "SHA-256" in str(raised.value)


def test_vendored_file_listed_in_source_md_but_missing_is_reported(
    tmp_path: Path,
) -> None:
    files = {
        name: content
        for name, content in VALID_BUILD_FILES.items()
        if name != "avcodec-63.dll"
    }
    write_build(
        tmp_path / "vendor" / "build", files, recorded_checksums=VALID_BUILD_FILES
    )

    with pytest.raises(FfmpegUnavailableError) as raised:
        make_locator(tmp_path).locate()

    assert "avcodec-63.dll" in str(raised.value)


def test_program_that_does_not_answer_version_is_reported(tmp_path: Path) -> None:
    write_build(tmp_path / "vendor" / "build", VALID_BUILD_FILES)

    with pytest.raises(FfmpegUnavailableError) as raised:
        make_locator(
            tmp_path, version_reader=FakeVersionReader(failing_program="ffprobe")
        ).locate()

    assert "ffprobe.exe" in str(raised.value)
    assert "-version" in str(raised.value)


def test_system_path_is_the_last_resort_and_is_not_validated(tmp_path: Path) -> None:
    installation = make_locator(
        tmp_path,
        programs_on_path={
            "ffmpeg": "/usr/local/bin/ffmpeg",
            "ffprobe": "/usr/bin/ffprobe",
        },
    ).locate()

    assert installation.source is FfmpegSource.SYSTEM_PATH
    # yt-dlp busca en el PATH por su cuenta; ffmpeg y ffprobe pueden estar en
    # carpetas distintas.
    assert installation.ffmpeg_location is None
    assert installation.is_validated is False


def test_no_ffmpeg_anywhere_explains_every_option(tmp_path: Path) -> None:
    with pytest.raises(FfmpegUnavailableError) as raised:
        make_locator(tmp_path, programs_on_path={"ffmpeg": "/usr/bin/ffmpeg"}).locate()

    message = str(raised.value)
    assert "ffmpeg_path" in message
    assert "git lfs pull" in message
    assert "PATH" in message


def test_checksums_are_reused_while_size_and_date_do_not_change(
    tmp_path: Path,
) -> None:
    bin_directory = write_build(tmp_path / "vendor" / "build", VALID_BUILD_FILES)
    make_locator(tmp_path).locate()
    library = bin_directory / "avcodec-63.dll"
    original_times = (library.stat().st_atime_ns, library.stat().st_mtime_ns)

    # Mismo tamaño y misma fecha: la caché evita leer el archivo de nuevo.
    library.write_bytes(DLL_CONTENT.replace(b"fake", b"FAKE"))
    os.utime(library, ns=original_times)
    make_locator(tmp_path).locate()

    # Otra fecha: se vuelve a calcular el SHA-256 y se detecta el cambio.
    os.utime(library, ns=(original_times[0], original_times[1] + 1_000_000_000))
    with pytest.raises(FfmpegUnavailableError):
        make_locator(tmp_path).locate()


def test_unreadable_cache_is_rebuilt(tmp_path: Path) -> None:
    write_build(tmp_path / "vendor" / "build", VALID_BUILD_FILES)
    cache_file = tmp_path / "state" / "ffmpeg-verification.json"
    cache_file.parent.mkdir()
    cache_file.write_text("{not json", encoding="utf-8")

    installation = make_locator(tmp_path).locate()

    assert installation.source is FfmpegSource.VENDORED
    assert cache_file.read_text(encoding="utf-8").startswith("{")


@pytest.mark.skipif(os.name == "nt", reason="the fake program is a POSIX script")
def test_read_program_version_returns_the_first_line(tmp_path: Path) -> None:
    program = tmp_path / "fake-ffmpeg"
    program.write_text(
        f"#!{sys.executable}\nprint('ffmpeg version 9.0')\nprint('built with gcc')\n",
        encoding="utf-8",
    )
    program.chmod(0o755)

    assert read_program_version(program) == "ffmpeg version 9.0"


@pytest.mark.skipif(os.name == "nt", reason="the fake program is a POSIX script")
def test_read_program_version_fails_when_the_program_fails(tmp_path: Path) -> None:
    program = tmp_path / "broken-ffmpeg"
    program.write_text(
        f"#!{sys.executable}\nimport sys\nsys.exit(1)\n", encoding="utf-8"
    )
    program.chmod(0o755)

    with pytest.raises(OSError, match="exit code 1"):
        read_program_version(program)
