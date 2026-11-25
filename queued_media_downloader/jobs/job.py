"""La entidad job: unidad de trabajo de la cola."""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import NewType, Self

from queued_media_downloader.jobs.download_options import DownloadOptions
from queued_media_downloader.jobs.failure_reason import FailureReason
from queued_media_downloader.jobs.job_events import PlaylistEntriesFound
from queued_media_downloader.jobs.job_kind import JobKind
from queued_media_downloader.jobs.job_lifecycle import ensure_transition_allowed
from queued_media_downloader.jobs.job_status import JobStatus
from queued_media_downloader.jobs.media_key import MediaKey
from queued_media_downloader.jobs.playlist_context import PlaylistContext
from queued_media_downloader.jobs.playlist_entry import PlaylistEntry

JobId = NewType("JobId", int)

# Carpeta, dentro de la de descargas, con una subcarpeta de parciales por job.
PARTIAL_DIRECTORY_NAME = ".partial"


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

    @classmethod
    def new_playlist_child(
        cls,
        parent: "Job",
        playlist_batch: PlaylistEntriesFound,
        playlist_entry: PlaylistEntry,
        *,
        is_duplicate: bool,
    ) -> Self:
        """Crea, aún sin guardar, el job hijo de una entrada del lote (UC-04).

        Nace SKIPPED si la entrada no está disponible (A3) o si su contenido ya
        tiene una descarga (A2); si no, PENDING. Hereda las opciones de la
        expansión salvo whole_playlist: --playlist decide sobre la URL
        encolada, no sobre las de sus entradas (ADR-0027).
        """
        if parent.job_id is None:
            message = "Only a stored job can have playlist children"
            raise ValueError(message)
        if parent.kind is not JobKind.EXPANSION:
            message = (
                f"Only an EXPANSION job has playlist children, not {parent.kind.value}"
            )
            raise ValueError(message)
        is_skipped = is_duplicate or not playlist_entry.is_available
        return cls(
            job_id=None,
            kind=playlist_entry.kind,
            status=JobStatus.SKIPPED if is_skipped else JobStatus.PENDING,
            url=playlist_entry.url,
            download_options=replace(parent.download_options, whole_playlist=False),
            parent_id=parent.job_id,
            playlist_context=_playlist_context_of(playlist_batch, playlist_entry),
            media_key=playlist_entry.media_key,
            title=playlist_entry.title,
        )

    def partial_directory(self) -> Path:
        """Carpeta propia de los archivos parciales del job (T44, riesgo R-14).

        yt-dlp escribe ahí todo lo intermedio (.part, .ytdl, partes .f<id>,
        .temp) y solo mueve el archivo terminado a la carpeta de descargas.
        Todo lo que contiene es de este job: el id no se reutiliza nunca
        (migración 0003), aunque dos jobs den el mismo nombre a sus archivos.
        Está dentro de la carpeta de descargas para que mover el archivo final
        sea renombrarlo, sin copiarlo entre unidades.

        Raises:
            ValueError: Si el job aún no está guardado.
        """
        if self.job_id is None:
            message = "Only a stored job has a partial directory"
            raise ValueError(message)
        return (
            self.download_options.download_directory
            / PARTIAL_DIRECTORY_NAME
            / f"job-{self.job_id}"
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

    def recover_from_interruption(self) -> Self:
        """Corrige un job que un cierre inesperado dejó a medias (UC-06, paso 2).

        Un job en curso vuelve a la cola y conserva lo que registró, como el
        formato elegido; uno con la cancelación pedida queda cancelado.

        Raises:
            ValueError: Si el job no estaba en curso ni cancelándose.
        """
        match self.status:
            case JobStatus.RUNNING:
                return self.transition_to(JobStatus.PENDING)
            case JobStatus.CANCELLATION_REQUESTED:
                return self.transition_to(JobStatus.CANCELLED)
            case _:
                message = f"A {self.status.value} job was not interrupted"
                raise ValueError(message)

    def _as_download(self, media_key: MediaKey, title: str) -> Self:
        """Copia de una expansión convertida en la descarga de media_key."""
        if self.kind is not JobKind.EXPANSION:
            message = f"Only an EXPANSION job finds its media, not {self.kind.value}"
            raise ValueError(message)
        return replace(self, kind=JobKind.DOWNLOAD, media_key=media_key, title=title)


def _playlist_context_of(
    playlist_batch: PlaylistEntriesFound, playlist_entry: PlaylistEntry
) -> PlaylistContext:
    """Posición de la entrada en su playlist.

    El número de entradas que declara el sitio puede estar desactualizado; si
    la entrada queda fuera de él, se trata como desconocido.
    """
    playlist_entry_count = playlist_batch.playlist_entry_count
    if (
        playlist_entry_count is not None
        and playlist_entry.playlist_index > playlist_entry_count
    ):
        playlist_entry_count = None
    return PlaylistContext(
        playlist_id=playlist_batch.playlist_id,
        playlist_title=playlist_batch.playlist_title,
        playlist_index=playlist_entry.playlist_index,
        playlist_entry_count=playlist_entry_count,
    )
