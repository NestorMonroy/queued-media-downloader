"""Una entrada de una playlist, tal como la encuentra la expansión."""

from dataclasses import dataclass

from queued_media_downloader.jobs.job_kind import JobKind
from queued_media_downloader.jobs.media_key import MediaKey


@dataclass(frozen=True, slots=True, kw_only=True)
class PlaylistEntry:
    """Lo que hace falta para crear el job hijo de una entrada (UC-04).

    kind es EXPANSION si la entrada es a su vez una playlist (A1) y DOWNLOAD
    si es un contenido. media_key y title pueden faltar: la expansión no
    resuelve las entradas, solo las enumera. Una entrada no disponible
    (privada o eliminada, A3) da un hijo SKIPPED.
    """

    url: str
    playlist_index: int
    kind: JobKind
    title: str | None
    media_key: MediaKey | None
    is_available: bool

    def __post_init__(self) -> None:
        """Rechaza una entrada sin URL o con una posición imposible."""
        if not self.url:
            message = "PlaylistEntry requires a non-empty url"
            raise ValueError(message)
        if self.playlist_index < 1:
            message = f"playlist_index must start at 1, not {self.playlist_index}"
            raise ValueError(message)
