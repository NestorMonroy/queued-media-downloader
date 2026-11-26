"""Comando purge: borra de la cola los jobs terminados (UC-10)."""

import argparse
import sys

from queued_media_downloader.command_line.command_settings import (
    load_command_settings,
)
from queued_media_downloader.command_line.composition_root import (
    open_job_store,
    output_claims_directory,
)
from queued_media_downloader.command_line.exit_code import ExitCode
from queued_media_downloader.configuration import SettingsError
from queued_media_downloader.job_queue import PurgeFinishedJobs
from queued_media_downloader.jobs import JobStatus
from queued_media_downloader.media_extraction import OutputClaims


def add_purge_command(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Registra el comando purge (diseño, Parte 2, §4.1)."""
    purge_parser = commands.add_parser(
        "purge", help="delete finished jobs from the queue (files are kept)"
    )
    purge_parser.add_argument("--completed", action="store_true")
    purge_parser.add_argument("--cancelled", action="store_true")
    purge_parser.set_defaults(run_command=run_purge_command)


def run_purge_command(arguments: argparse.Namespace) -> int:
    """Borra los jobs COMPLETED y/o CANCELLED; sin opciones, ambos."""
    statuses = {
        status
        for status, chosen in (
            (JobStatus.COMPLETED, arguments.completed),
            (JobStatus.CANCELLED, arguments.cancelled),
        )
        if chosen
    } or {JobStatus.COMPLETED, JobStatus.CANCELLED}
    try:
        settings = load_command_settings({})
        with open_job_store(settings.state_directory) as job_store:
            output_claims = OutputClaims(output_claims_directory(settings))
            result = PurgeFinishedJobs(job_store, output_claims).execute(statuses)
    except SettingsError as usage_error:
        print(f"{arguments.program_name}: error: {usage_error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    noun = "job" if result.deleted_job_count == 1 else "jobs"
    print(f"Purged {result.deleted_job_count} {noun}; downloaded files are kept")
    for playlist in result.kept_playlists:
        print(f"Kept job {playlist.job_id}: its playlist has unfinished entries")
    return ExitCode.SUCCESS
