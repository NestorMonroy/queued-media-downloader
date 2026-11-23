"""Apertura de la base de datos SQLite de la cola."""

import sqlite3
from pathlib import Path

from queued_media_downloader.job_storage.sqlite_migrations import apply_migrations

BUSY_TIMEOUT_MILLISECONDS = 5000

# Diseño, Parte 2, §2.3: un escritor y varios lectores a la vez (WAL), claves
# foráneas activas, espera ante bloqueos y menos escrituras forzadas a disco.
CONNECTION_PRAGMAS = (
    "PRAGMA journal_mode = WAL",
    "PRAGMA foreign_keys = ON",
    f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MILLISECONDS}",
    "PRAGMA synchronous = NORMAL",
)


def open_database(database_path: Path) -> sqlite3.Connection:
    """Abre la base de datos, aplica los PRAGMAs y deja el esquema al día."""
    connection = sqlite3.connect(database_path)
    for pragma in CONNECTION_PRAGMAS:
        connection.execute(pragma)
    apply_migrations(connection)
    return connection
