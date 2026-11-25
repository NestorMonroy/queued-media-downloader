"""Archivos parciales que deja el formato de un intento de descarga anterior."""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Nombres que da yt-dlp 2026.10.26 a lo que aún descarga (YoutubeDL.process_info):
# un formato único va a <base>.<ext>; cada parte de un formato unido
# ("137+140"), a <base>.f<id>.<ext>. A ambos les añade .part, y .ytdl si
# descarga por fragmentos.
PARTIAL_FILE_SUFFIX_PATTERN = r"\.[^.]+\.(?:part|ytdl)"


def remove_partial_files_of(final_path: Path, previous_format_id: str) -> list[Path]:
    """Borra los parciales que dejó previous_format_id junto a final_path.

    Solo se borran los nombres que yt-dlp da a ese formato con el nombre base de
    final_path, nunca un archivo terminado. Un archivo que otro proceso tiene
    abierto (Windows no permite borrarlo) o que ya no existe se deja y no hace
    fallar la descarga: la limpieza puede repetirse sin efectos.

    Returns:
        Los archivos borrados.
    """
    partial_name = _partial_name_pattern(final_path.stem, previous_format_id)
    removed_paths = []
    for candidate_path in sorted(final_path.parent.iterdir()):
        if not partial_name.fullmatch(candidate_path.name):
            continue
        try:
            candidate_path.unlink()
        except FileNotFoundError:
            continue
        except OSError as unlink_error:
            logger.warning(
                "Could not remove partial file of a previous format: %s", unlink_error
            )
            continue
        logger.info("Removed partial file of a previous format: %s", candidate_path)
        removed_paths.append(candidate_path)
    return removed_paths


def _partial_name_pattern(base_name: str, format_id: str) -> re.Pattern[str]:
    """Nombres de los parciales de format_id con ese nombre base."""
    format_ids = format_id.split("+")
    if len(format_ids) == 1:
        return re.compile(re.escape(base_name) + PARTIAL_FILE_SUFFIX_PATTERN)
    part_markers = "|".join(re.escape(f"f{part_id}") for part_id in format_ids)
    return re.compile(
        rf"{re.escape(base_name)}\.(?:{part_markers}){PARTIAL_FILE_SUFFIX_PATTERN}"
    )
