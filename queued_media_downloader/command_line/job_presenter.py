"""Presentación en la consola de lo que les ocurre a los jobs, en inglés."""

from typing import TextIO

from queued_media_downloader.jobs import (
    DownloadProgressed,
    FormatSelected,
    Job,
    JobCancelled,
    JobCompleted,
    JobEvent,
    JobFailed,
    JobRequest,
    JobRequestType,
    JobStarted,
    JobStatus,
    PlaylistEntriesFound,
    PostprocessingProgressed,
    PostprocessingStage,
    SingleMediaFound,
)
from queued_media_downloader.workers import WorkerMessage

# Pasos internos de yt-dlp que no le dicen nada al usuario.
INTERNAL_POSTPROCESSOR_NAMES = frozenset({"MoveFiles"})
BYTES_PER_UNIT = 1024
BYTE_UNITS = ("B", "KiB", "MiB", "GiB", "TiB")


class JobPresenter:
    """Escribe una línea por job event; el progreso ya llega limitado."""

    def __init__(self, output: TextIO) -> None:
        """Escribe en output, normalmente la salida estándar."""
        self._output = output

    def present(self, message: WorkerMessage, job: Job | None) -> None:
        """Escribe la línea del job event, si tiene algo que mostrar.

        job es el job tal como quedó tras el job event; None si el job event
        solo informa del avance.
        """
        if job is not None and job.status is JobStatus.CANCELLED:
            # También un fallo o un contenido encontrado mientras se cancelaba.
            description: str | None = "cancelled"
        else:
            description = _describe(message.job_event, job)
        if description is not None:
            print(f"Job {message.job_id}: {description}", file=self._output, flush=True)

    def present_job_request(self, job_request: JobRequest, job: Job) -> None:
        """Escribe qué hizo run con una job request de cancel o retry."""
        if job_request.request_type is JobRequestType.RETRY:
            description = _describe_retry(job)
        elif job.status is JobStatus.CANCELLED:
            description = "cancelled"
        elif job.status is JobStatus.CANCELLATION_REQUESTED:
            description = "cancellation requested"
        else:
            description = f"already {job.status.value}; nothing to cancel"
        print(f"Job {job_request.job_id}: {description}", file=self._output, flush=True)


def _describe_retry(job: Job) -> str:
    """Resultado de una job request RETRY (UC-07)."""
    if job.status is JobStatus.PENDING:
        return f"queued again (attempt {job.attempt_count + 1})"
    return f"not retried; it is {job.status.value}"


def _describe(job_event: JobEvent, job: Job | None) -> str | None:
    """Texto del job event; None si no se muestra."""
    if isinstance(job_event, DownloadProgressed | PostprocessingProgressed):
        return _describe_progress_event(job_event)
    match job_event:
        case JobStarted():
            return "started"
        case SingleMediaFound() | PlaylistEntriesFound():
            return _describe_discovery(job_event, job)
        case FormatSelected(selected_format_id=selected_format_id):
            return f"format {selected_format_id}"
        case JobCompleted(output_path=output_path):
            return _describe_completion(output_path)
        case JobFailed(failure_reason=failure_reason, failure_message=failure_message):
            return f"failed ({failure_reason.value}): {failure_message}"
        case JobCancelled():
            return "cancelled"


def _describe_discovery(
    job_event: SingleMediaFound | PlaylistEntriesFound, job: Job | None
) -> str:
    """Lo que encontró una expansión: un contenido o un lote de una playlist."""
    if isinstance(job_event, PlaylistEntriesFound):
        entry_count = len(job_event.playlist_entries)
        noun = "entry" if entry_count == 1 else "entries"
        playlist = (
            repr(job_event.playlist_title)
            if job_event.playlist_title
            else job_event.playlist_id
        )
        return f"found {entry_count} {noun} in playlist {playlist}"
    if job is not None and job.status is JobStatus.SKIPPED:
        return f"found {job_event.title!r}, skipped: already downloaded or in the queue"
    return f"found {job_event.title!r}"


def _describe_completion(output_path: str | None) -> str:
    """Un job sin archivo, como una expansión, solo se da por completado."""
    if output_path is None:
        return "completed"
    return f"completed, saved to {output_path}"


def _describe_progress_event(
    job_event: DownloadProgressed | PostprocessingProgressed,
) -> str | None:
    """Del postprocesado solo se muestra el inicio de los que entiende el usuario."""
    if isinstance(job_event, DownloadProgressed):
        return _describe_progress(job_event)
    if (
        job_event.postprocessing_stage is not PostprocessingStage.STARTED
        or job_event.postprocessor_name in INTERNAL_POSTPROCESSOR_NAMES
    ):
        return None
    return f"running {job_event.postprocessor_name}"


def _describe_progress(progress: DownloadProgressed) -> str:
    """Porcentaje, tamaño, velocidad y tiempo restante, con lo que se conozca."""
    if not progress.total_bytes:
        return f"{_format_bytes(progress.downloaded_bytes)} downloaded"
    percent = 100 * progress.downloaded_bytes / progress.total_bytes
    description = f"{percent:.1f}% of {_format_bytes(progress.total_bytes)}"
    if progress.bytes_per_second is not None:
        description += f" at {_format_bytes(progress.bytes_per_second)}/s"
    if progress.eta_seconds is not None:
        description += f", ETA {progress.eta_seconds} s"
    return description


def _format_bytes(byte_count: float) -> str:
    """Tamaño con la unidad binaria más grande que lo deja por encima de 1."""
    size = float(byte_count)
    for unit in BYTE_UNITS[:-1]:
        if size < BYTES_PER_UNIT:
            return f"{size:.1f} {unit}"
        size /= BYTES_PER_UNIT
    return f"{size:.1f} {BYTE_UNITS[-1]}"
