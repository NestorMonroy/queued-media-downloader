"""Caso de uso UC-01: comprobar que el entorno está listo para descargar."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from queued_media_downloader.ffmpeg_discovery import (
    FfmpegInstallation,
    FfmpegLocator,
    FfmpegSource,
    FfmpegUnavailableError,
)
from queued_media_downloader.media_extraction import JavaScriptRuntime

# Cómo se nombra cada origen de ffmpeg en el detalle de la comprobación.
FFMPEG_SOURCE_NAMES = {
    FfmpegSource.CONFIGURED: "from ffmpeg_path",
    FfmpegSource.VENDORED: "bundled",
    FfmpegSource.SYSTEM_PATH: "from PATH, version not validated",
}
DENO_NOT_FOUND = (
    "not found. Run 'uv sync' in the project folder to install the deno of the project"
)


class CheckOutcome(StrEnum):
    """Resultado de una comprobación; solo FAILED impide usar la cola."""

    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class EnvironmentCheck:
    """Resultado de comprobar un componente del entorno, explicado en inglés."""

    component: str
    outcome: CheckOutcome
    detail: str


class DiagnoseEnvironment:
    """Comprueba ffmpeg, ffprobe, deno y la base de datos (UC-01, pasos 6 a 9).

    Cada comprobación se ejecuta aunque falle otra, para que el usuario vea
    todos los problemas de una vez.
    """

    def __init__(
        self,
        *,
        ffmpeg_locator: FfmpegLocator,
        find_javascript_runtime: Callable[[], JavaScriptRuntime | None],
        open_database: Callable[[], int],
    ) -> None:
        """Recibe cómo localizar cada componente.

        Args:
            ffmpeg_locator: Localiza y verifica ffmpeg y ffprobe.
            find_javascript_runtime: Devuelve el deno que usará yt-dlp.
            open_database: Abre la base de datos, aplica las migraciones que
                falten y devuelve la versión del esquema.
        """
        self._ffmpeg_locator = ffmpeg_locator
        self._find_javascript_runtime = find_javascript_runtime
        self._open_database = open_database

    def execute(self) -> list[EnvironmentCheck]:
        """Devuelve una comprobación por componente, en orden de UC-01."""
        return [
            *self._check_ffmpeg(),
            self._check_deno(),
            self._check_database(),
        ]

    def _check_ffmpeg(self) -> list[EnvironmentCheck]:
        """Comprueba ffmpeg y ffprobe; si ffmpeg no es utilizable, queda una sola."""
        try:
            installation = self._ffmpeg_locator.locate()
        except FfmpegUnavailableError as ffmpeg_error:
            return [EnvironmentCheck("ffmpeg", CheckOutcome.FAILED, str(ffmpeg_error))]
        outcome = (
            CheckOutcome.PASSED if installation.is_validated else CheckOutcome.WARNING
        )
        return [
            EnvironmentCheck("ffmpeg", outcome, _describe_ffmpeg(installation)),
            EnvironmentCheck("ffprobe", outcome, installation.ffprobe_version),
        ]

    def _check_deno(self) -> EnvironmentCheck:
        """Deno es necesario para YouTube; una versión antigua no sirve."""
        deno = self._find_javascript_runtime()
        if deno is None:
            return EnvironmentCheck("deno", CheckOutcome.FAILED, DENO_NOT_FOUND)
        if not deno.is_supported:
            detail = (
                f"deno {deno.version} in {deno.path} is older than "
                f"{deno.minimum_version}, the minimum yt-dlp supports"
            )
            return EnvironmentCheck("deno", CheckOutcome.FAILED, detail)
        return EnvironmentCheck(
            "deno", CheckOutcome.PASSED, f"deno {deno.version} in {deno.path}"
        )

    def _check_database(self) -> EnvironmentCheck:
        """La base de datos se abre y queda migrada a la última versión."""
        try:
            schema_version = self._open_database()
        except (sqlite3.Error, OSError) as database_error:
            return EnvironmentCheck(
                "database", CheckOutcome.FAILED, str(database_error)
            )
        return EnvironmentCheck(
            "database", CheckOutcome.PASSED, f"schema version {schema_version}"
        )


def _describe_ffmpeg(installation: FfmpegInstallation) -> str:
    """Versión, origen y carpeta de ffmpeg."""
    description = (
        f"{installation.ffmpeg_version}, {FFMPEG_SOURCE_NAMES[installation.source]}"
    )
    if installation.ffmpeg_location is not None:
        description += f", in {installation.ffmpeg_location}"
    return description
