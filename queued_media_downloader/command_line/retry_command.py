"""Comando retry: registra el reintento de jobs (UC-07)."""

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
from queued_media_downloader.job_queue import RetryJob, RetryJobResult
from queued_media_downloader.job_storage import JobNotFoundError
from queued_media_downloader.jobs import JobId


def add_retry_command(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Registra el comando retry (diseño, Parte 2, §4.1)."""
    retry_parser = commands.add_parser("retry", help="retry failed or cancelled jobs")
    targets = retry_parser.add_mutually_exclusive_group(required=True)
    targets.add_argument("job_ids", nargs="*", type=int, default=[], metavar="JOB_ID")
    targets.add_argument("--all-failed", action="store_true")
    retry_parser.set_defaults(run_command=run_retry_command)


def run_retry_command(arguments: argparse.Namespace) -> int:
    """Registra los reintentos; run los aplica.

    Returns:
        SUCCESS si se registraron, aunque algún job no se pudiera reintentar;
        USAGE_ERROR si un job no existe, no se indicó ninguno o la
        configuración no es válida, sin registrar ninguno.
    """
    if not arguments.all_failed and not arguments.job_ids:
        print(f"{arguments.program_name}: error: give JOB_ID or --all-failed")
        return ExitCode.USAGE_ERROR
    try:
        settings = load_command_settings({})
        with open_job_store_and_inbox(settings.state_directory) as (job_store, inbox):
            retry_job = RetryJob(job_store, inbox)
            if arguments.all_failed:
                result = retry_job.execute_all_failed()
            else:
                result = retry_job.execute([JobId(j) for j in arguments.job_ids])
    except (SettingsError, JobNotFoundError) as usage_error:
        print(f"{arguments.program_name}: error: {usage_error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    _report(result)
    return ExitCode.SUCCESS


def _report(result: RetryJobResult) -> None:
    for job_id in result.requested:
        print(f"Retry requested for job {job_id}")
    for job in result.not_retriable:
        print(f"Job {job.job_id} is {job.status.value}; only FAILED or CANCELLED")
    if not result.requested and not result.not_retriable:
        print("No failed jobs to retry")
