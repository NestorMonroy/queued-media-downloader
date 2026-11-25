"""JobStore en memoria con las mismas reglas que SqliteJobStore."""

from collections.abc import Collection, Sequence
from dataclasses import replace

from queued_media_downloader.job_storage import (
    DuplicateActiveDownloadError,
    DuplicateOutputPathError,
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

    def create_many(self, jobs: Sequence[Job]) -> list[JobId]:
        """Guarda los jobs en orden; si uno falla, no queda ninguno del lote."""
        jobs_before = dict(self._jobs)
        try:
            return [self.create(job) for job in jobs]
        except DuplicateActiveDownloadError:
            self._jobs = jobs_before
            raise

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
        self._ensure_output_path_is_free(job, job.job_id)
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

    def get_with_status(self, statuses: Collection[JobStatus]) -> list[Job]:
        """Devuelve los jobs en alguno de esos estados, en orden de creación."""
        return [job for job in self._jobs.values() if job.status in statuses]

    def has_active_download(self, media_key: MediaKey, *, audio_only: bool) -> bool:
        """Indica si hay una descarga no omitida del contenido con ese tipo."""
        return any(
            _is_active_download_of(job, media_key, audio_only=audio_only)
            for job in self._jobs.values()
        )

    def _ensure_output_path_is_free(self, job: Job, job_id: JobId) -> None:
        """Aplica la regla del índice unique_output_path (T44)."""
        if job.output_path is None:
            return
        if any(
            other.output_path == job.output_path
            for other_id, other in self._jobs.items()
            if other_id != job_id
        ):
            raise DuplicateOutputPathError(job.output_path)

    def _ensure_no_duplicate(self, job: Job, job_id: JobId) -> None:
        """Aplica la regla del índice único de descargas activas (ADR-0012).

        Igual que en SQLite, compara el contenido y el tipo de archivo.
        """
        media_key = job.media_key
        audio_only = job.download_options.audio_only
        if media_key is None or not _is_active_download_of(
            job, media_key, audio_only=audio_only
        ):
            return
        for other_id, other in self._jobs.items():
            if other_id != job_id and _is_active_download_of(
                other, media_key, audio_only=audio_only
            ):
                raise DuplicateActiveDownloadError(media_key)


def _is_active_download_of(job: Job, media_key: MediaKey, *, audio_only: bool) -> bool:
    """Un job DOWNLOAD de ese contenido y ese tipo que no está SKIPPED."""
    return (
        job.kind is JobKind.DOWNLOAD
        and job.media_key == media_key
        and job.download_options.audio_only is audio_only
        and job.status is not JobStatus.SKIPPED
    )
