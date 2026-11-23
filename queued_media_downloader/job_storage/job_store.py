"""Contrato de persistencia de los jobs."""

from typing import Protocol

from queued_media_downloader.jobs import Job, JobId, MediaKey


class JobNotFoundError(Exception):
    """No existe ningún job guardado con el identificador pedido."""

    def __init__(self, job_id: JobId) -> None:
        """Guarda el identificador y compone el mensaje para los logs."""
        self.job_id = job_id
        super().__init__(f"Job {job_id} does not exist")


class DuplicateActiveDownloadError(Exception):
    """Ya existe un job de descarga no omitido para el mismo contenido (ADR-0012)."""

    def __init__(self, media_key: MediaKey) -> None:
        """Guarda la media key duplicada y compone el mensaje para los logs."""
        self.media_key = media_key
        super().__init__(
            "A download for "
            f"{media_key.extractor_key}:{media_key.media_id} is already queued"
        )


class JobStore(Protocol):
    """Guarda y recupera los jobs de la cola."""

    def create(self, job: Job) -> JobId:
        """Guarda un job nuevo y devuelve el identificador que se le asignó."""
        ...

    def get(self, job_id: JobId) -> Job:
        """Devuelve el job guardado.

        Raises:
            JobNotFoundError: Si no existe.
        """
        ...

    def update(self, job: Job) -> None:
        """Sustituye el job guardado por esta versión.

        Raises:
            JobNotFoundError: Si no existe.
            DuplicateActiveDownloadError: Si dejaría dos descargas activas del
                mismo contenido.
        """
        ...

    def get_next_pending(self, limit: int) -> list[Job]:
        """Devuelve hasta limit jobs pendientes, en orden de creación."""
        ...

    def has_active_download(self, media_key: MediaKey) -> bool:
        """Indica si hay un job de descarga no omitido para ese contenido."""
        ...
