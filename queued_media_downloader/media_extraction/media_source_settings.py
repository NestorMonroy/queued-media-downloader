"""Valores de configuración que necesita una MediaSource."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class MediaSourceSettings:
    """Configuración común a todos los jobs de un worker.

    Es inmutable y serializable: viaja al proceso del worker junto con la
    fábrica de MediaSource.
    """

    cache_directory: Path
    ffmpeg_location: Path | None
    max_filename_length: int
