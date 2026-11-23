"""Localiza ffmpeg en el orden de ADR-0006: configurado, vendor/ y PATH."""

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from queued_media_downloader.ffmpeg_discovery.checksum_cache import ChecksumCache
from queued_media_downloader.ffmpeg_discovery.ffmpeg_locator import (
    FfmpegInstallation,
    FfmpegSource,
    FfmpegUnavailableError,
)
from queued_media_downloader.ffmpeg_discovery.vendored_build import (
    recorded_checksums,
    verify_vendored_build,
)

# Build incluida en el repositorio, fijada como la versión de yt-dlp (ADR-0018).
VENDORED_BUILD_NAME = "n9.0.2-39-g7adfbe40dc-win64-lgpl-shared"
VERSION_TIMEOUT_SECONDS = 30
PLATFORM_EXECUTABLE_SUFFIX = ".exe" if os.name == "nt" else ""
NOT_FOUND_MESSAGE = (
    "ffmpeg was not found. Set ffmpeg_path to your own ffmpeg, run "
    "'git lfs pull' in the project folder to get the bundled build in "
    "vendor/ffmpeg, or add ffmpeg and ffprobe to PATH."
)

ReadVersion = Callable[[Path], str]
FindOnPath = Callable[[str], str | None]


def read_program_version(program_path: Path) -> str:
    """Primera línea de `program -version`, sin el copyright que la sigue.

    Raises:
        OSError: Si el programa no arranca, no termina a tiempo o falla.
    """
    try:
        completed_process = subprocess.run(
            [str(program_path), "-version"],
            capture_output=True,
            text=True,
            timeout=VERSION_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as timeout_error:
        message = f"{program_path} did not finish within {VERSION_TIMEOUT_SECONDS} s"
        raise OSError(message) from timeout_error
    if completed_process.returncode != 0:
        message = f"{program_path} ended with exit code {completed_process.returncode}"
        raise OSError(message)
    first_line = completed_process.stdout.partition("\n")[0]
    version, _, _ = first_line.partition(" Copyright")
    return version.strip()


class FileSystemFfmpegLocator:
    """Busca ffmpeg y ffprobe en disco y comprueba que responden.

    Una ruta configurada o una build incluida que no sirven son un error: no se
    pasa en silencio al siguiente paso, para que el usuario sepa qué ffmpeg usa.
    """

    def __init__(
        self,
        *,
        configured_path: Path | None,
        vendored_build_directory: Path,
        verification_cache_file: Path,
        read_version: ReadVersion = read_program_version,
        find_on_path: FindOnPath = shutil.which,
        executable_suffix: str = PLATFORM_EXECUTABLE_SUFFIX,
    ) -> None:
        """Configura dónde buscar; read_version y find_on_path se sustituyen en pruebas.

        Args:
            configured_path: Valor de ffmpeg_path: una carpeta con ffmpeg y
                ffprobe, o el propio ffmpeg; None si no se configuró.
            vendored_build_directory: Carpeta de la build incluida.
            verification_cache_file: Archivo de la caché de SHA-256.
            read_version: Devuelve la versión de un programa.
            find_on_path: Busca un programa en el PATH.
            executable_suffix: Extensión de los ejecutables (.exe en Windows).
        """
        self._configured_path = configured_path
        self._vendored_build_directory = vendored_build_directory
        self._verification_cache_file = verification_cache_file
        self._read_version = read_version
        self._find_on_path = find_on_path
        self._executable_suffix = executable_suffix

    def locate(self) -> FfmpegInstallation:
        """Devuelve el primer ffmpeg del orden de ADR-0006 y lo verifica."""
        if self._configured_path is not None:
            return self._configured_installation(self._configured_path)
        checksums = recorded_checksums(self._vendored_build_directory)
        # La build incluida es de Windows: en otro sistema no tiene un ffmpeg
        # ejecutable y se pasa al PATH.
        if self._program_name("ffmpeg") in checksums:
            return self._vendored_installation(checksums)
        return self._system_path_installation()

    def _configured_installation(self, configured_path: Path) -> FfmpegInstallation:
        """Instalación de la carpeta configurada o de la del ffmpeg configurado."""
        directory = (
            configured_path if configured_path.is_dir() else configured_path.parent
        )
        for program in ("ffmpeg", "ffprobe"):
            if not (directory / self._program_name(program)).is_file():
                message = (
                    f"ffmpeg_path points to {configured_path}, but "
                    f"{self._program_name(program)} was not found in {directory}"
                )
                raise FfmpegUnavailableError(message)
        return self._installation(FfmpegSource.CONFIGURED, directory)

    def _vendored_installation(self, checksums: dict[str, str]) -> FfmpegInstallation:
        """La build incluida, tras comprobar cada archivo contra SOURCE.md."""
        checksum_cache = ChecksumCache(self._verification_cache_file)
        try:
            verify_vendored_build(
                self._vendored_build_directory, checksums, checksum_cache
            )
        finally:
            # Lo calculado se guarda también si un archivo falla.
            checksum_cache.save()
        return self._installation(
            FfmpegSource.VENDORED, self._vendored_build_directory / "bin"
        )

    def _system_path_installation(self) -> FfmpegInstallation:
        """Instalación del PATH; yt-dlp buscará allí ffmpeg y ffprobe por su cuenta."""
        ffmpeg = self._find_on_path("ffmpeg")
        ffprobe = self._find_on_path("ffprobe")
        if ffmpeg is None or ffprobe is None:
            raise FfmpegUnavailableError(NOT_FOUND_MESSAGE)
        return FfmpegInstallation(
            source=FfmpegSource.SYSTEM_PATH,
            ffmpeg_location=None,
            ffmpeg_version=self._version_of(Path(ffmpeg)),
            ffprobe_version=self._version_of(Path(ffprobe)),
        )

    def _installation(
        self, source: FfmpegSource, directory: Path
    ) -> FfmpegInstallation:
        """Instalación de una carpeta con ffmpeg y ffprobe que responden."""
        return FfmpegInstallation(
            source=source,
            ffmpeg_location=directory,
            ffmpeg_version=self._version_of(directory / self._program_name("ffmpeg")),
            ffprobe_version=self._version_of(directory / self._program_name("ffprobe")),
        )

    def _version_of(self, program_path: Path) -> str:
        """Versión del programa; un programa que no responde no se puede usar."""
        try:
            return self._read_version(program_path)
        except OSError as version_error:
            message = f"{program_path} did not answer -version: {version_error}"
            raise FfmpegUnavailableError(message) from version_error

    def _program_name(self, program: str) -> str:
        """Nombre del ejecutable en este sistema."""
        return f"{program}{self._executable_suffix}"
