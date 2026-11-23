"""Archivo de log de una ejecución: la consola queda para la presentación."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIRECTORY_NAME = "logs"
LOG_FILE_NAME = "queued-media-downloader.log"
# Acota lo que ocupa el log en un equipo modesto: el actual y tres anteriores.
MAX_LOG_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3
LOG_FORMAT = "%(asctime)s %(processName)s %(name)s %(levelname)s %(message)s"


def log_file_path(state_directory: Path) -> Path:
    """Ruta del archivo de log dentro de state_directory."""
    return state_directory / LOG_DIRECTORY_NAME / LOG_FILE_NAME


@contextmanager
def logging_to_file(state_directory: Path) -> Iterator[Path]:
    """Escribe todo el logging en el archivo de log mientras dura el bloque.

    Al terminar quita el handler y restaura el nivel anterior, para no dejar
    configuración ni el archivo abierto (en Windows quedaría bloqueado).
    Los registros de los workers llegan aquí a través del pool.
    """
    path = log_file_path(state_directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        path, maxBytes=MAX_LOG_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger = logging.getLogger()
    previous_level = root_logger.level
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)
    try:
        yield path
    finally:
        root_logger.removeHandler(file_handler)
        root_logger.setLevel(previous_level)
        file_handler.close()
