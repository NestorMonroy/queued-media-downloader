"""Identidad de un contenido descargable."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MediaKey:
    """Identifica un contenido por su extractor y su identificador en el sitio.

    Dos jobs con la misma media key descargarían el mismo contenido; la cola lo
    usa para no descargarlo dos veces (ADR-0012).
    """

    extractor_key: str
    media_id: str

    def __post_init__(self) -> None:
        """Rechaza claves con alguna parte vacía, que no identificarían nada."""
        if not self.extractor_key.strip() or not self.media_id.strip():
            message = "MediaKey requires a non-empty extractor_key and media_id"
            raise ValueError(message)
