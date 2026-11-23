"""La entidad job: unidad de trabajo de la cola."""

from dataclasses import dataclass, replace
from typing import NewType, Self

from queued_media_downloader.jobs.download_options import DownloadOptions
from queued_media_downloader.jobs.failure_reason import FailureReason
from queued_media_downloader.jobs.job_kind import JobKind
from queued_media_downloader.jobs.job_lifecycle import ensure_transition_allowed
from queued_media_downloader.jobs.job_status import JobStatus
from queued_media_downloader.jobs.media_key import MediaKey
from queued_media_downloader.jobs.playlist_context import PlaylistContext

JobId = NewType("JobId", int)


@dataclass(frozen=True, slots=True, kw_only=True)
class Job:
    """Unidad de trabajo de la cola: expandir una URL o descargar un contenido.

    Es inmutable: cada cambio devuelve una copia. Así puede viajar entre
    procesos sin que dos copias se modifiquen por separado. Un job hijo de una
    playlist guarda el job que lo creó (parent_id) y su posición en ella.
    """

    job_id: JobId | None
    kind: JobKind
    status: JobStatus
    url: str
    download_options: DownloadOptions
    parent_id: JobId | None = None
    playlist_context: PlaylistContext | None = None
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

    def start(self) -> Self:
        """El job se envía a un worker."""
        return self.transition_to(JobStatus.RUNNING)

    def found_single_media(self, media_key: MediaKey, title: str) -> Self:
        """La expansión encontró un solo contenido: vuelve a la cola como descarga."""
        return self._as_download(media_key, title).transition_to(JobStatus.PENDING)

    def skip_as_duplicate(self, media_key: MediaKey, title: str) -> Self:
        """La expansión encontró un contenido que ya tiene descarga (UC-03 A1)."""
        return self._as_download(media_key, title).transition_to(JobStatus.SKIPPED)

    def record_selected_format(self, selected_format_id: str) -> Self:
        """Guarda el formato elegido para reutilizarlo al reanudar (ADR-0010)."""
        return replace(self, selected_format_id=selected_format_id)

    def complete(self, output_path: str | None) -> Self:
        """El job terminó bien; output_path es None si no produjo un archivo."""
        return replace(self.transition_to(JobStatus.COMPLETED), output_path=output_path)

    def fail(self, failure_reason: FailureReason, failure_message: str) -> Self:
        """El job falló por failure_reason."""
        return replace(
            self.transition_to(JobStatus.FAILED),
            failure_reason=failure_reason,
            failure_message=failure_message,
        )

    def confirm_cancellation(self) -> Self:
        """El worker confirmó la cancelación pedida."""
        return self.transition_to(JobStatus.CANCELLED)

    def _as_download(self, media_key: MediaKey, title: str) -> Self:
        """Copia de una expansión convertida en la descarga de media_key."""
        if self.kind is not JobKind.EXPANSION:
            message = f"Only an EXPANSION job finds its media, not {self.kind.value}"
            raise ValueError(message)
        return replace(self, kind=JobKind.DOWNLOAD, media_key=media_key, title=title)
