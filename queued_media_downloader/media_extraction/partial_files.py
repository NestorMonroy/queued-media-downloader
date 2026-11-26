"""Archivos parciales de un job: viven en su propia carpeta (T44, R-14).

La carpeta se llama por el id del job (Job.partial_directory) y guarda, en
PARTIAL_OWNER_FILE_NAME, el owner token del job (id e instante de creación).
Si una copia antigua de la base de datos vuelve a dar ese id a otro job, la
carpeta no es suya: se aparta, sin borrar nada, y el job empieza de cero en
lugar de reanudar desde los parciales de otro contenido (ADR-0030).
"""

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

PARTIAL_OWNER_FILE_NAME = ".owner"
ORPHAN_PREFIX = "orphan-"


def prepare_partial_directory(partial_directory: Path, owner_token: str) -> None:
    """Deja la carpeta de parciales lista para el job de owner_token.

    Si la carpeta ya es del job, se conserva para reanudar. Si es de otro job
    o no dice de quién es y tiene archivos, se aparta como orphan-job-<id>-
    <instante>, con todo su contenido, y se crea una nueva.
    """
    if (
        partial_directory.exists()
        and not _belongs_to(partial_directory, owner_token)
        and any(partial_directory.iterdir())
    ):
        _set_aside(partial_directory)
    partial_directory.mkdir(parents=True, exist_ok=True)
    (partial_directory / PARTIAL_OWNER_FILE_NAME).write_text(
        owner_token, encoding="utf-8"
    )


def remove_partial_directory(partial_directory: Path, owner_token: str) -> None:
    """Borra la carpeta de parciales de un job que terminó o se purga.

    Solo si es de ese job (PARTIAL_OWNER_FILE_NAME): la de otro job con el
    mismo id se deja. Todo lo que hay en una carpeta propia es del job, así
    que no hace falta saber qué nombres dio yt-dlp a cada formato: también se
    van los parciales de un formato abandonado o de un intento interrumpido.
    Si no existe, no hace nada; si no se puede borrar, se registra y no hace
    fallar la operación. La carpeta común .partial no se borra: otro worker
    puede estar creando la suya dentro.
    """
    if not partial_directory.exists():
        return
    if not _belongs_to(partial_directory, owner_token):
        logger.warning(
            "Keeping %s: it does not belong to job %s",
            partial_directory,
            owner_token,
        )
        return
    try:
        shutil.rmtree(partial_directory)
    except OSError as removal_error:
        logger.warning(
            "Could not remove the partial files of a finished job: %s", removal_error
        )


def _belongs_to(partial_directory: Path, owner_token: str) -> bool:
    try:
        owner = (partial_directory / PARTIAL_OWNER_FILE_NAME).read_text(
            encoding="utf-8"
        )
    except OSError:
        return False
    return owner == owner_token


def _set_aside(partial_directory: Path) -> None:
    instant = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    orphan = partial_directory.with_name(
        f"{ORPHAN_PREFIX}{partial_directory.name}-{instant}"
    )
    partial_directory.rename(orphan)
    logger.warning(
        "%s belonged to another job with the same id; kept as %s",
        partial_directory,
        orphan,
    )
