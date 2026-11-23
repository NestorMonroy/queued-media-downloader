"""Job events: hechos que le ocurren a un job (diseño, Parte 1, §5).

Los publica un worker y los aplica el proceso principal. Son inmutables y solo
contienen tipos simples, para que pickle los lleve de un proceso a otro; nunca
llevan el info_dict de yt-dlp. No incluyen el identificador del job: lo añade
el mensaje del worker que los transporta.
"""

from dataclasses import dataclass
from enum import StrEnum

from queued_media_downloader.jobs.failure_reason import FailureReason
from queued_media_downloader.jobs.media_key import MediaKey
from queued_media_downloader.jobs.playlist_entry import PlaylistEntry


class PostprocessingStage(StrEnum):
    """Etapa de un postprocesado, como la unión de audio y video."""

    STARTED = "STARTED"
    PROCESSING = "PROCESSING"
    FINISHED = "FINISHED"


@dataclass(frozen=True, slots=True)
class JobStarted:
    """El worker empezó el job: PENDING pasa a RUNNING."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SingleMediaFound:
    """La URL de una expansión era un solo contenido: el job pasa a descarga."""

    media_key: MediaKey
    title: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PlaylistEntriesFound:
    """Un lote de entradas de la playlist de una expansión (UC-04, paso 3).

    La expansión publica las entradas por lotes, sin cargar la playlist entera
    en memoria. El job sigue RUNNING hasta JobCompleted. playlist_entry_count
    es el número de entradas que declara el sitio, si lo declara.
    """

    playlist_id: str
    playlist_title: str | None
    playlist_entries: tuple[PlaylistEntry, ...]
    playlist_entry_count: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FormatSelected:
    """Formato elegido antes de descargar; se reutiliza al reanudar."""

    selected_format_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DownloadProgressed:
    """Avance de una descarga; no se persiste, solo se presenta.

    Los valores que el sitio no informa quedan en None.
    """

    downloaded_bytes: int
    total_bytes: int | None
    bytes_per_second: float | None
    eta_seconds: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PostprocessingProgressed:
    """Avance de un postprocesado; no se persiste, solo se presenta."""

    postprocessor_name: str
    postprocessing_stage: PostprocessingStage


@dataclass(frozen=True, slots=True, kw_only=True)
class JobCompleted:
    """El job terminó bien.

    output_path es la ruta del archivo descargado; None si el job no produce
    un archivo.
    """

    output_path: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class JobFailed:
    """El job falló; failure_message explica el motivo al usuario."""

    failure_reason: FailureReason
    failure_message: str


@dataclass(frozen=True, slots=True)
class JobCancelled:
    """El worker confirmó la cancelación del job."""


JobEvent = (
    JobStarted
    | SingleMediaFound
    | PlaylistEntriesFound
    | FormatSelected
    | DownloadProgressed
    | PostprocessingProgressed
    | JobCompleted
    | JobFailed
    | JobCancelled
)
