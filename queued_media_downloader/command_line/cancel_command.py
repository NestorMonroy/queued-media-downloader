"""Comando cancel: registra la cancelación de jobs (UC-05)."""

import argparse
import sys

from queued_media_downloader.command_line.command_settings import (
    load_command_settings,
)
from queued_media_downloader.command_line.composition_root import (
    open_job_store_and_inbox,
)
from queued_media_downloader.command_line.exit_code import ExitCode
from queued_media_downloader.configuration import SettingsError
from queued_media_downloader.job_queue import CancelJob, CancelJobResult
from queued_media_downloader.job_storage import JobNotFoundError
from queued_media_downloader.jobs import JobId


def add_cancel_command(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Registra el comando cancel (diseño, Parte 2, §4.1)."""
    cancel_parser = commands.add_parser("cancel", help="cancel queued or running jobs")
    cancel_parser.add_argument("job_ids", nargs="+", type=int, metavar="JOB_ID")
    cancel_parser.set_defaults(run_command=run_cancel_command)


def run_cancel_command(arguments: argparse.Namespace) -> int:
    """Registra las cancelaciones; run las aplica (UC-05, pasos 2 y 3).

    Returns:
        SUCCESS si se registraron, aunque algún job ya hubiera terminado;
        USAGE_ERROR si un job no existe o la configuración no es válida, sin
        registrar ninguna.
    """
    job_ids = [JobId(job_id) for job_id in arguments.job_ids]
    try:
        settings = load_command_settings({})
        with open_job_store_and_inbox(settings.state_directory) as (job_store, inbox):
            result = CancelJob(job_store, inbox).execute(job_ids)
    except (SettingsError, JobNotFoundError) as usage_error:
        print(f"{arguments.program_name}: error: {usage_error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    _report(result)
    return ExitCode.SUCCESS


def _report(result: CancelJobResult) -> None:
    """Qué se registró y qué no hacía falta cancelar (A7)."""
    for job_id, descendant_count in result.requested.items():
        entries = ""
        if descendant_count:
            noun = "entry" if descendant_count == 1 else "entries"
            entries = f" and {descendant_count} playlist {noun}"
        print(f"Cancellation requested for job {job_id}{entries}")
    for job_id, entry_count in result.entries_of_finished_playlists.items():
        noun = "entry" if entry_count == 1 else "entries"
        print(
            f"Cancellation requested for {entry_count} unfinished playlist {noun} "
            f"of job {job_id}"
        )
    for finished_job in result.already_finished:
        print(
            f"Job {finished_job.job_id} already finished "
            f"({finished_job.status.value}); nothing to cancel"
        )
