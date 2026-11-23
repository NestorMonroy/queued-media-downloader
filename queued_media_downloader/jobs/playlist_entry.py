"""Una entrada de una playlist, tal como la encuentra la expansión."""

from dataclasses import dataclass

from queued_media_downloader.jobs.job_kind import JobKind
from queued_media_downloader.jobs.media_key import MediaKey


@dataclass(frozen=True, slots=True, kw_only=True)
class PlaylistEntry:
    """Lo que hace falta para crear el job hijo de una entrada (UC-04).

    kind es EXPANSION si la entrada es a su vez una playlist (A1) o no se
    sabe qué es, y DOWNLOAD si es un contenido. Un DOWNLOAD trae siempre su
    media_key, que la regla de duplicados necesita (A2). title puede faltar:
    la expansión no resuelve las entradas, solo las enumera. Una entrada no disponible
    (privada o eliminada, A3) da un hijo SKIPPED.
    """

    url: str
    playlist_index: int
    kind: JobKind
    title: str | None
    media_key: MediaKey | None
    is_available: bool

    def __post_init__(self) -> None:
        """Rechaza una entrada sin URL, sin posición válida o sin media key."""
        if not self.url:
            message = "PlaylistEntry requires a non-empty url"
            raise ValueError(message)
        if self.playlist_index < 1:
            message = f"playlist_index must start at 1, not {self.playlist_index}"
            raise ValueError(message)
        if self.kind is JobKind.DOWNLOAD and self.media_key is None:
            message = "A DOWNLOAD PlaylistEntry requires its media_key"
            raise ValueError(message)
