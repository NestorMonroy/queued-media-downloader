"""Comandos list y show: consultan la cola sin modificarla (UC-08, UC-09)."""

import argparse
import sys

from queued_media_downloader.command_line.command_settings import (
    load_command_settings,
)
from queued_media_downloader.command_line.composition_root import open_job_store
from queued_media_downloader.command_line.exit_code import ExitCode
from queued_media_downloader.configuration import SettingsError
from queued_media_downloader.job_queue import JobDetails, ListJobs, ShowJob
from queued_media_downloader.job_storage import JobNotFoundError
from queued_media_downloader.jobs import Job, JobId, JobStatus


def add_list_and_show_commands(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Registra los comandos list y show (diseño, Parte 2, §4.1)."""
    list_parser = commands.add_parser("list", help="list the queued jobs")
    list_parser.add_argument(
        "--status", choices=[status.value for status in JobStatus], metavar="STATUS"
    )
    list_parser.add_argument("--parent", type=int, metavar="JOB_ID")
    list_parser.set_defaults(run_command=run_list_command)
    show_parser = commands.add_parser("show", help="show every detail of a job")
    show_parser.add_argument("job_id", type=int, metavar="JOB_ID")
    show_parser.set_defaults(run_command=run_show_command)


def run_list_command(arguments: argparse.Namespace) -> int:
    """Escribe una línea por job: id, tipo, estado, título y motivo de fallo."""
    status = None if arguments.status is None else JobStatus(arguments.status)
    parent_id = None if arguments.parent is None else JobId(arguments.parent)
    try:
        settings = load_command_settings({})
        with open_job_store(settings.state_directory) as job_store:
            jobs = ListJobs(job_store).execute(status, parent_id)
    except (SettingsError, JobNotFoundError) as usage_error:
        print(f"{arguments.program_name}: error: {usage_error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    for job in jobs:
        print(_job_line(job))
    if not jobs:
        print("No jobs")
    return ExitCode.SUCCESS


def run_show_command(arguments: argparse.Namespace) -> int:
    """Escribe todos los datos de un job y, si es una playlist, sus hijos."""
    try:
        settings = load_command_settings({})
        with open_job_store(settings.state_directory) as job_store:
            details = ShowJob(job_store).execute(JobId(arguments.job_id))
    except (SettingsError, JobNotFoundError) as usage_error:
        print(f"{arguments.program_name}: error: {usage_error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    for label, value in _detail_lines(details):
        print(f"{label + ':':<16} {value}")
    return ExitCode.SUCCESS


def _job_line(job: Job) -> str:
    failure = f"  ({job.failure_reason.value})" if job.failure_reason else ""
    return (
        f"{job.job_id:>6}  {job.kind.value:<9}  {job.status.value:<22}  "
        f"{job.title or job.url}{failure}"
    )


def _detail_lines(details: JobDetails) -> list[tuple[str, object]]:
    job = details.job
    options = job.download_options
    lines: list[tuple[str, object]] = [
        ("Job", job.job_id),
        ("Kind", job.kind.value),
        ("Status", job.status.value),
        ("URL", job.url),
        ("Title", job.title or "-"),
        ("Attempts", job.attempt_count + 1),
        ("Format", job.selected_format_id or options.format_selector),
        ("Audio only", "yes" if options.audio_only else "no"),
        ("Download folder", options.download_directory),
        ("Output", job.output_path or "-"),
    ]
    if job.parent_id is not None and job.playlist_context is not None:
        context = job.playlist_context
        playlist = context.playlist_title or context.playlist_id
        lines.append(
            (
                "Playlist",
                f"job {job.parent_id}, '{playlist}', #{context.playlist_index}",
            )
        )
    if job.failure_reason is not None:
        lines.append(("Failure", f"{job.failure_reason.value}: {job.failure_message}"))
    if details.children_by_status:
        summary = ", ".join(
            f"{count} {status.value}"
            for status, count in details.children_by_status.items()
        )
        lines.append(("Entries", summary))
    return lines
