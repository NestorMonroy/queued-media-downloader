"""Comando enqueue: une la configuración con el caso de uso EnqueueMedia."""

import argparse
import sys

from queued_media_downloader.command_line.command_settings import (
    load_command_settings,
)
from queued_media_downloader.command_line.composition_root import open_job_store
from queued_media_downloader.command_line.exit_code import ExitCode
from queued_media_downloader.configuration import SettingsError
from queued_media_downloader.job_queue import EnqueueMedia, InvalidUrlError
from queued_media_downloader.jobs import DownloadOptions


def add_enqueue_command(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Registra el comando enqueue y sus opciones (diseño, Parte 2, §4.1)."""
    enqueue_parser = commands.add_parser("enqueue", help="add URLs to the queue")
    enqueue_parser.add_argument("urls", nargs="+", metavar="URL")
    enqueue_parser.add_argument("--format", dest="format_selector", metavar="SELECTOR")
    enqueue_parser.add_argument("--audio-only", action="store_true")
    enqueue_parser.add_argument("--download-directory", metavar="DIR")
    enqueue_parser.set_defaults(run_command=run_enqueue_command)


def run_enqueue_command(arguments: argparse.Namespace) -> int:
    """Encola las URLs con las download options de esta invocación.

    Returns:
        SUCCESS si se encolaron todas; USAGE_ERROR si una URL o un valor de
        configuración no es válido, sin encolar ninguna.
    """
    try:
        settings = load_command_settings(
            {
                "default_format_selector": arguments.format_selector,
                "download_directory": arguments.download_directory,
            }
        )
        download_options = DownloadOptions(
            format_selector=settings.default_format_selector,
            download_directory=settings.download_directory,
            output_template=settings.single_media_output_template,
            audio_only=arguments.audio_only,
        )
        with open_job_store(settings.state_directory) as job_store:
            job_ids = EnqueueMedia(job_store).execute(arguments.urls, download_options)
    except (SettingsError, InvalidUrlError) as usage_error:
        print(f"{arguments.program_name}: error: {usage_error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    for job_id in job_ids:
        print(f"Queued job {job_id}")
    return ExitCode.SUCCESS
