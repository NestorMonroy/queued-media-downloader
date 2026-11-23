"""Comando run: ejecuta la cola hasta que no queden jobs pendientes (UC-03)."""

import argparse
import sys

from queued_media_downloader.command_line.command_settings import (
    load_command_settings,
)
from queued_media_downloader.command_line.composition_root import (
    open_job_store,
    open_worker_pool,
)
from queued_media_downloader.command_line.exit_code import ExitCode
from queued_media_downloader.command_line.job_presenter import JobPresenter
from queued_media_downloader.configuration import SettingsError
from queued_media_downloader.job_queue import RunQueue


def add_run_command(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Registra el comando run y sus opciones (diseño, Parte 2, §4.1)."""
    run_parser = commands.add_parser("run", help="run the queued jobs")
    run_parser.add_argument("--worker-count", metavar="N")
    run_parser.set_defaults(run_command=run_run_command)


def run_run_command(arguments: argparse.Namespace) -> int:
    """Ejecuta la cola y resume el resultado.

    Returns:
        SUCCESS si ningún job falló, JOBS_FAILED si alguno falló y
        USAGE_ERROR si la configuración no es válida.
    """
    try:
        settings = load_command_settings({"worker_count": arguments.worker_count})
    except SettingsError as settings_error:
        print(f"{arguments.program_name}: error: {settings_error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    with (
        open_job_store(settings.state_directory) as job_store,
        open_worker_pool(settings) as worker_pool,
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
