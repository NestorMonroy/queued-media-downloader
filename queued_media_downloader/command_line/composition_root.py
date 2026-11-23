"""Crea las implementaciones de los contratos para la línea de comandos.

Es el único módulo que importa el interior de otros componentes (diseño,
Parte 1, §3, regla 3).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from queued_media_downloader.job_storage import JobStore
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_store import SqliteJobStore

DATABASE_FILE_NAME = "queue.sqlite3"


@contextmanager
def open_job_store(state_directory: Path) -> Iterator[JobStore]:
    """Abre el job store de state_directory y cierra su conexión al terminar."""
    state_directory.mkdir(parents=True, exist_ok=True)
    connection = open_database(state_directory / DATABASE_FILE_NAME)
    try:
        yield SqliteJobStore(connection)
    finally:
        connection.close()
