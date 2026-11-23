"""JobStore en memoria con las mismas reglas que SqliteJobStore."""

from dataclasses import replace

from queued_media_downloader.job_storage import (
    DuplicateActiveDownloadError,
    JobNotFoundError,
)
from queued_media_downloader.jobs import Job, JobId, JobKind, JobStatus, MediaKey


class InMemoryJobStore:
    """Guarda los jobs en un diccionario, en orden de creación."""

    def __init__(self) -> None:
        """Empieza vacío; los identificadores empiezan en 1."""
        self._jobs: dict[JobId, Job] = {}

    def create(self, job: Job) -> JobId:
        """Guarda un job nuevo y devuelve el identificador asignado."""
        job_id = JobId(len(self._jobs) + 1)
        self._ensure_no_duplicate(job, job_id)
        self._jobs[job_id] = replace(job, job_id=job_id)
        return job_id

    def get(self, job_id: JobId) -> Job:
        """Devuelve el job guardado; JobNotFoundError si no existe."""
        if job_id not in self._jobs:
            raise JobNotFoundError(job_id)
        return self._jobs[job_id]

    def update(self, job: Job) -> None:
        """Sustituye el job guardado por esta versión."""
        if job.job_id is None or job.job_id not in self._jobs:
            raise JobNotFoundError(JobId(0) if job.job_id is None else job.job_id)
        self._ensure_no_duplicate(job, job.job_id)
        self._jobs[job.job_id] = job

    def get_next_pending(self, limit: int) -> list[Job]:
        """Devuelve hasta limit jobs pendientes, en orden de creación."""
        pending_jobs = [
            job for job in self._jobs.values() if job.status is JobStatus.PENDING
        ]
        return pending_jobs[:limit]

    def all_jobs(self) -> list[Job]:
        """Todos los jobs guardados, en orden de creación (solo para pruebas)."""
        return list(self._jobs.values())

    def has_active_download(self, media_key: MediaKey) -> bool:
        """Indica si hay un job de descarga no omitido para ese contenido."""
        return any(
            _is_active_download_of(job, media_key) for job in self._jobs.values()
        )

    def _ensure_no_duplicate(self, job: Job, job_id: JobId) -> None:
        """Aplica la regla del índice único de descargas activas (ADR-0012)."""
        if job.media_key is None or not _is_active_download_of(job, job.media_key):
            return
        for other_id, other in self._jobs.items():
            if other_id != job_id and _is_active_download_of(other, job.media_key):
                raise DuplicateActiveDownloadError(job.media_key)


def _is_active_download_of(job: Job, media_key: MediaKey) -> bool:
    """Un job DOWNLOAD de ese contenido que no está SKIPPED."""
    return (
        job.kind is JobKind.DOWNLOAD
        and job.media_key == media_key
        and job.status is not JobStatus.SKIPPED
    )
