"""Comando run: ejecuta la cola hasta que no queden jobs pendientes (UC-03)."""

import argparse
import sys

from queued_media_downloader.command_line.command_settings import (
    load_command_settings,
)
from queued_media_downloader.command_line.composition_root import (
    create_ffmpeg_locator,
    open_job_store,
    open_worker_pool,
)
from queued_media_downloader.command_line.exit_code import ExitCode
from queued_media_downloader.command_line.job_presenter import JobPresenter
from queued_media_downloader.configuration import SettingsError
from queued_media_downloader.ffmpeg_discovery import (
    FfmpegInstallation,
    FfmpegSource,
    FfmpegUnavailableError,
)
from queued_media_downloader.job_queue import RunQueue

# Cómo se presenta cada origen de ffmpeg al arrancar la cola.
FFMPEG_SOURCE_DESCRIPTIONS = {
    FfmpegSource.CONFIGURED: "Using ffmpeg from ffmpeg_path",
    FfmpegSource.VENDORED: "Using bundled ffmpeg",
    FfmpegSource.SYSTEM_PATH: "Using ffmpeg from PATH (version not validated)",
}


def add_run_command(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Registra el comando run y sus opciones (diseño, Parte 2, §4.1)."""
    run_parser = commands.add_parser("run", help="run the queued jobs")
    run_parser.add_argument("--worker-count", metavar="N")
    run_parser.set_defaults(run_command=run_run_command)


def run_run_command(arguments: argparse.Namespace) -> int:
    """Verifica ffmpeg, ejecuta la cola y resume el resultado.

    Returns:
        SUCCESS si ningún job falló, JOBS_FAILED si alguno falló y
        USAGE_ERROR si la configuración no es válida o no hay un ffmpeg
        utilizable; en ese caso no se ejecuta ningún job.
    """
    try:
        settings = load_command_settings({"worker_count": arguments.worker_count})
        # Se verifica antes de ejecutar nada: un ffmpeg roto se descubre al
        # arrancar y no al final de la primera descarga (ADR-0006).
        ffmpeg_installation = create_ffmpeg_locator(settings).locate()
    except (SettingsError, FfmpegUnavailableError) as usage_error:
        print(f"{arguments.program_name}: error: {usage_error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    print(_describe_ffmpeg(ffmpeg_installation))
    with (
        open_job_store(settings.state_directory) as job_store,
        open_worker_pool(settings, ffmpeg_installation.ffmpeg_location) as worker_pool,
    ):
        run_result = RunQueue(
            job_store, worker_pool, present=JobPresenter(sys.stdout).present
        ).execute()
    if run_result.failed_job_count == 0:
        print("All jobs finished")
        return ExitCode.SUCCESS
    noun = "job" if run_result.failed_job_count == 1 else "jobs"
    print(f"All jobs finished; {run_result.failed_job_count} {noun} failed")
    return ExitCode.JOBS_FAILED


def _describe_ffmpeg(ffmpeg_installation: FfmpegInstallation) -> str:
    """Qué ffmpeg se usa y su versión, para saber con qué se une cada archivo."""
    description = FFMPEG_SOURCE_DESCRIPTIONS[ffmpeg_installation.source]
    return f"{description}: {ffmpeg_installation.ffmpeg_version}"
