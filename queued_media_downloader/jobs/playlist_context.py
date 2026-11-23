"""Posición de un job hijo dentro de la playlist que lo creó."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class PlaylistContext:
    """Playlist de la que salió un job hijo y su posición en ella (UC-04).

    Se guarda con el job para construir su plantilla de salida sin volver a
    extraer la playlist. El título y el número de entradas pueden no
    conocerse: la expansión recorre las entradas de forma perezosa.
    """

    playlist_id: str
    playlist_title: str | None
    playlist_index: int
    playlist_entry_count: int | None

    def __post_init__(self) -> None:
        """Rechaza una playlist sin identificador o una posición imposible."""
        if not self.playlist_id:
            message = "PlaylistContext requires a non-empty playlist_id"
            raise ValueError(message)
        if self.playlist_index < 1 or (
            self.playlist_entry_count is not None
            and self.playlist_index > self.playlist_entry_count
        ):
            message = (
                f"playlist_index {self.playlist_index} is not a position in a "
                f"playlist of {self.playlist_entry_count} entries"
            )
            raise ValueError(message)
