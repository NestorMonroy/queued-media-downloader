import sqlite3
from collections.abc import Callable
from pathlib import Path

from queued_media_downloader.diagnostics import (
    CheckOutcome,
    DiagnoseEnvironment,
    EnvironmentCheck,
)
from queued_media_downloader.ffmpeg_discovery import (
    FfmpegInstallation,
    FfmpegSource,
    FfmpegUnavailableError,
)
from queued_media_downloader.media_extraction import JavaScriptRuntime, YtDlpVersions

BUNDLED_FFMPEG = FfmpegInstallation(
    source=FfmpegSource.VENDORED,
    ffmpeg_location=Path("vendor/ffmpeg/build/bin"),
    ffmpeg_version="ffmpeg version n9.0.2-39-g7adfbe40dc",
    ffprobe_version="ffprobe version n9.0.2-39-g7adfbe40dc",
)
SUPPORTED_DENO = JavaScriptRuntime(
    name="deno",
    path=Path(".venv/Scripts/deno.exe"),
    version="2.9.8",
    minimum_version="2.3.0",
    is_supported=True,
)


class FakeFfmpegLocator:
    """Devuelve la instalación indicada o lanza el error indicado."""

    def __init__(
        self,
        installation: FfmpegInstallation | None = BUNDLED_FFMPEG,
        error: FfmpegUnavailableError | None = None,
    ) -> None:
        """Guarda lo que devolverá locate."""
        self._installation = installation
        self._error = error

    def locate(self) -> FfmpegInstallation:
        """Como FfmpegLocator.locate."""
        if self._error is not None:
            raise self._error
        assert self._installation is not None
        return self._installation


def database_at_version_2() -> int:
    """Base de datos que se abre y queda en la versión 2 del esquema."""
    return 2


def failing_database() -> int:
    """Base de datos que no se puede abrir."""
    message = "unable to open database file"
    raise sqlite3.OperationalError(message)


INSTALLED_YT_DLP = YtDlpVersions(yt_dlp="2026.11.23", challenge_solver="0.8.0")


def diagnose(
    ffmpeg_locator: FakeFfmpegLocator | None = None,
    javascript_runtime: JavaScriptRuntime | None = SUPPORTED_DENO,
    open_database: Callable[[], int] = database_at_version_2,
    yt_dlp_versions: YtDlpVersions = INSTALLED_YT_DLP,
) -> dict[str, EnvironmentCheck]:
    """Ejecuta el diagnóstico con dobles y devuelve las comprobaciones por nombre."""
    checks = DiagnoseEnvironment(
        ffmpeg_locator=ffmpeg_locator or FakeFfmpegLocator(),
        find_yt_dlp_versions=lambda: yt_dlp_versions,
        find_javascript_runtime=lambda: javascript_runtime,
        open_database=open_database,
    ).execute()
    return {check.component: check for check in checks}


def test_every_component_passes_in_a_ready_environment() -> None:
    checks = diagnose()

    assert list(checks) == ["ffmpeg", "ffprobe", "yt-dlp", "deno", "database"]
    assert {check.outcome for check in checks.values()} == {CheckOutcome.PASSED}
    # Las rutas se muestran con el separador del sistema (barra invertida en Windows).
    assert checks["ffmpeg"].detail == (
        "ffmpeg version n9.0.2-39-g7adfbe40dc, bundled, in "
        f"{BUNDLED_FFMPEG.ffmpeg_location}"
    )
    assert checks["ffprobe"].detail == "ffprobe version n9.0.2-39-g7adfbe40dc"
    assert checks["deno"].detail == f"deno 2.9.8 in {SUPPORTED_DENO.path}"
    assert checks["database"].detail == "schema version 2"


def test_ffmpeg_from_path_is_a_warning_not_a_failure() -> None:
    from_path = FfmpegInstallation(
        source=FfmpegSource.SYSTEM_PATH,
        ffmpeg_location=None,
        ffmpeg_version="ffmpeg version 6.1.1-3ubuntu5",
        ffprobe_version="ffprobe version 6.1.1-3ubuntu5",
    )

    checks = diagnose(ffmpeg_locator=FakeFfmpegLocator(installation=from_path))

    assert checks["ffmpeg"].outcome is CheckOutcome.WARNING
    assert "PATH" in checks["ffmpeg"].detail
    assert "not validated" in checks["ffmpeg"].detail
    assert checks["ffprobe"].outcome is CheckOutcome.WARNING


def test_unusable_ffmpeg_fails_with_its_remedy_and_the_rest_is_still_checked() -> None:
    error = FfmpegUnavailableError("ffmpeg.exe is a Git LFS pointer. Run git lfs pull")

    checks = diagnose(ffmpeg_locator=FakeFfmpegLocator(error=error))

    assert checks["ffmpeg"].outcome is CheckOutcome.FAILED
    assert "git lfs pull" in checks["ffmpeg"].detail
    assert "ffprobe" not in checks
    assert checks["deno"].outcome is CheckOutcome.PASSED
    assert checks["database"].outcome is CheckOutcome.PASSED


def test_missing_deno_fails_and_asks_for_uv_sync() -> None:
    checks = diagnose(javascript_runtime=None)

    assert checks["deno"].outcome is CheckOutcome.FAILED
    assert "uv sync" in checks["deno"].detail


def test_deno_older_than_yt_dlp_supports_fails_with_the_minimum_version() -> None:
    old_deno = JavaScriptRuntime(
        name="deno",
        path=Path("/usr/bin/deno"),
        version="2.1.0",
        minimum_version="2.3.0",
        is_supported=False,
    )

    checks = diagnose(javascript_runtime=old_deno)

    assert checks["deno"].outcome is CheckOutcome.FAILED
    assert "2.1.0" in checks["deno"].detail
    assert "2.3.0" in checks["deno"].detail


def test_database_that_cannot_be_opened_fails_with_the_reason() -> None:
    checks = diagnose(open_database=failing_database)

    assert checks["database"].outcome is CheckOutcome.FAILED
    assert "unable to open database file" in checks["database"].detail


def test_yt_dlp_and_its_challenge_solver_versions_are_reported() -> None:
    check = diagnose()["yt-dlp"]

    assert check.outcome is CheckOutcome.PASSED
    assert check.detail == "yt-dlp 2026.11.23 with yt-dlp-ejs 0.8.0"


def test_missing_challenge_solver_fails_and_asks_for_uv_sync() -> None:
    check = diagnose(
        yt_dlp_versions=YtDlpVersions(yt_dlp="2026.11.23", challenge_solver=None)
    )["yt-dlp"]

    assert check.outcome is CheckOutcome.FAILED
    assert "yt-dlp-ejs" in check.detail
    assert "uv sync" in check.detail
