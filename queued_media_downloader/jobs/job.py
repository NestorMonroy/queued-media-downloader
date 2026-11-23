"""La entidad job: unidad de trabajo de la cola."""

from dataclasses import dataclass, replace
from typing import NewType, Self

from queued_media_downloader.jobs.download_options import DownloadOptions
from queued_media_downloader.jobs.failure_reason import FailureReason
from queued_media_downloader.jobs.job_kind import JobKind
from queued_media_downloader.jobs.job_lifecycle import ensure_transition_allowed
from queued_media_downloader.jobs.job_status import JobStatus
from queued_media_downloader.jobs.media_key import MediaKey

JobId = NewType("JobId", int)


@dataclass(frozen=True, slots=True, kw_only=True)
class Job:
    """Unidad de trabajo de la cola: expandir una URL o descargar un contenido.

    Es inmutable: cada cambio devuelve una copia. Así puede viajar entre
    procesos sin que dos copias se modifiquen por separado.
    """

    job_id: JobId | None
    kind: JobKind
    status: JobStatus
    url: str
    download_options: DownloadOptions
    media_key: MediaKey | None = None
    title: str | None = None
    selected_format_id: str | None = None
    attempt_count: int = 0
    failure_reason: FailureReason | None = None
    failure_message: str | None = None
    output_path: str | None = None

    @classmethod
    def new_expansion(cls, url: str, download_options: DownloadOptions) -> Self:
        """Crea el job con el que entra toda URL a la cola, aún sin guardar."""
        return cls(
            job_id=None,
            kind=JobKind.EXPANSION,
            status=JobStatus.PENDING,
            url=url,
            download_options=download_options,
        )

    def transition_to(self, target_status: JobStatus) -> Self:
        """Devuelve una copia en target_status si el ciclo de vida lo permite.

        Raises:
            InvalidJobTransitionError: Si la transición no está permitida.
        """
        ensure_transition_allowed(self.status, target_status)
        return replace(self, status=target_status)
