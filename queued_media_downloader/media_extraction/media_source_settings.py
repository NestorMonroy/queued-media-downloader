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
    # Reclamaciones de nombres finales (output_claims, R-14): una por cola.
    output_claims_directory: Path
    ffmpeg_location: Path | None
    max_filename_length: int
    progress_interval_seconds: float
    # Entradas por lote de PlaylistEntriesFound (UC-04, paso 3).
    playlist_batch_size: int = 50
