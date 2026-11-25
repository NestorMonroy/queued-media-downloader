"""Archivos parciales de un job: viven en su propia carpeta (T44, R-14)."""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def remove_partial_directory(partial_directory: Path) -> None:
    """Borra la carpeta de parciales de un job que terminó su descarga.

    Todo lo que hay en ella es del job (Job.partial_directory), así que no hace
    falta saber qué nombres dio yt-dlp a cada formato: también se van los
    parciales de un formato abandonado o de un intento interrumpido. Si no
    existe, no hace nada; si no se puede borrar, se registra y no hace fallar
    la descarga, que ya terminó. La carpeta común .partial no se borra: otro
    worker puede estar creando la suya dentro.
    """
    if not partial_directory.exists():
        return
    try:
        shutil.rmtree(partial_directory)
    except OSError as removal_error:
        logger.warning(
            "Could not remove the partial files of a finished job: %s", removal_error
        )
