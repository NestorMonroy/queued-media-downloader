"""Archivos parciales que deja un intento de descarga anterior."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# yt-dlp guarda lo descargado en <nombre>.part y el estado de los fragmentos en
# <nombre>.ytdl; los formatos que se unen llevan .f<id> en el nombre.
PARTIAL_FILE_SUFFIXES = (".part", ".ytdl")


def remove_partial_files_of(final_path: Path) -> list[Path]:
    """Borra los parciales del mismo contenido que quedan junto a final_path.

    Tras una descarga terminada, sus propios parciales ya no existen: los que
    quedan con el mismo nombre base son de un formato anterior (UC-06, A1). El
    nombre base lleva el id del contenido, así que no toca los de otro.

    Returns:
        Los archivos borrados.
    """
    base_name_prefix = f"{final_path.stem}."
    removed_paths = [
        path
        for path in final_path.parent.iterdir()
        if path.name.startswith(base_name_prefix)
        and path.name.endswith(PARTIAL_FILE_SUFFIXES)
    ]
    for removed_path in removed_paths:
        removed_path.unlink()
        logger.info("Removed partial file of a previous format: %s", removed_path)
    return removed_paths
