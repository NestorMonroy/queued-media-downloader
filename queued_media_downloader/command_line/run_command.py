"""Comando run: ejecuta la cola hasta que no queden jobs pendientes (UC-03)."""

import argparse
import sys
from pathlib import Path

from queued_media_downloader.command_line.command_settings import (
    load_command_settings,
)
from queued_media_downloader.command_line.composition_root import (
    create_ffmpeg_locator,
    open_job_store_and_inbox,
    open_worker_pool,
)
from queued_media_downloader.command_line.console_interruption import (
    InterruptionRequest,
    handling_interruptions,
)
from queued_media_downloader.command_line.exit_code import ExitCode
from queued_media_downloader.command_line.job_presenter import JobPresenter
from queued_media_downloader.command_line.log_file import logging_to_file
from queued_media_downloader.configuration import Settings, SettingsError
from queued_media_downloader.ffmpeg_discovery import (
    FfmpegInstallation,
    FfmpegSource,
    FfmpegUnavailableError,
)
from queued_media_downloader.job_queue import (
    RecoverInterruptedJobs,
    RecoveryResult,
    RunQueue,
    RunQueueResult,
)

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
    run_parser.add_argument(
        "--keep-waiting",
        action="store_true",
        help="do not stop when the queue is empty; wait for new jobs until Ctrl+C",
    )
    run_parser.set_defaults(run_command=run_run_command)


def run_run_command(arguments: argparse.Namespace) -> int:
    """Verifica ffmpeg, ejecuta la cola y resume el resultado.

    Returns:
        SUCCESS si ningún job falló, JOBS_FAILED si alguno falló,
        INTERRUPTED si el User pulsó Ctrl+C y USAGE_ERROR si la configuración
        no es válida o no hay un ffmpeg utilizable; en ese caso no se ejecuta
        ningún job.
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
    # El manejador abarca también el arranque y el apagado del pool y el cierre
    # de la base de datos: ningún Ctrl+C los corta a medias ni deja una traza.
    with handling_interruptions() as interruption_request:
        try:
            outcome = _run_queue(
                settings, ffmpeg_installation, arguments, interruption_request
            )
        except KeyboardInterrupt:
            # Segundo Ctrl+C mientras arrancaba el pool: no había jobs en curso.
            print("Stopped; interrupted jobs will resume on the next run")
            return ExitCode.INTERRUPTED
    if outcome is None:
        return ExitCode.INTERRUPTED
    run_result, log_path = outcome
    if run_result.interrupted:
        print("Interrupted; the running jobs will resume on the next run")
        return ExitCode.INTERRUPTED
    if run_result.failed_job_count == 0:
        print("All jobs finished")
        return ExitCode.SUCCESS
    noun = "job" if run_result.failed_job_count == 1 else "jobs"
    print(f"All jobs finished; {run_result.failed_job_count} {noun} failed")
    print(f"See the log for details: {log_path}")
    return ExitCode.JOBS_FAILED


def _run_queue(
    settings: Settings,
    ffmpeg_installation: FfmpegInstallation,
    arguments: argparse.Namespace,
    interruption_request: InterruptionRequest,
) -> tuple[RunQueueResult, Path] | None:
    """Recupera los jobs a medias y ejecuta la cola.

    Returns:
        El resultado y la ruta del log; None si un segundo Ctrl+C detuvo la
        cola sin esperar a que los jobs se detuvieran (los jobs en curso siguen
        RUNNING y continúan en el siguiente run, UC-06).
    """
    with (
        logging_to_file(settings.state_directory) as log_path,
        open_job_store_and_inbox(settings.state_directory) as (job_store, inbox),
        open_worker_pool(settings, ffmpeg_installation.ffmpeg_location) as worker_pool,
    ):
        try:
            # Antes de enviar ningún job (UC-06): nada queda RUNNING sin worker.
            _report_recovery(RecoverInterruptedJobs(job_store).execute())
            presenter = JobPresenter(sys.stdout)
            run_result = RunQueue(
                job_store,
                worker_pool,
                inbox,
                present=presenter.present,
                present_job_request=presenter.present_job_request,
                cancellation_grace_seconds=settings.cancellation_grace_seconds,
                stop_requested=interruption_request,
                keep_waiting=arguments.keep_waiting,
            ).execute()
        except KeyboardInterrupt:
            # Segundo Ctrl+C: sin esperar a que los jobs se detengan.
            worker_pool.shut_down(immediately=True)
            print("Stopped; interrupted jobs will resume on the next run")
            return None
    return run_result, log_path


def _report_recovery(recovery_result: RecoveryResult) -> None:
    """Avisa de los jobs que dejó a medias un cierre inesperado, si los hay."""
    recovered_job_count = recovery_result.recovered_job_count
    if recovered_job_count == 0:
        return
    noun = "job" if recovered_job_count == 1 else "jobs"
    print(
        f"Recovered {recovered_job_count} interrupted {noun}: "
        f"{recovery_result.requeued_job_count} back in the queue, "
        f"{recovery_result.cancelled_job_count} cancelled"
    )


def _describe_ffmpeg(ffmpeg_installation: FfmpegInstallation) -> str:
    """Qué ffmpeg se usa y su versión, para saber con qué se une cada archivo."""
    description = FFMPEG_SOURCE_DESCRIPTIONS[ffmpeg_installation.source]
    return f"{description}: {ffmpeg_installation.ffmpeg_version}"
