"""Fixtures de las pruebas de los comandos."""

import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_store import SqliteJobStore
from queued_media_downloader.jobs import Job, JobId

ENVIRONMENT_PREFIX = "QUEUED_MEDIA_DOWNLOADER_"


@pytest.fixture
def state_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Aísla la prueba del entorno real: estado y descargas en tmp_path."""
    for variable in list(os.environ):
        if variable.startswith(ENVIRONMENT_PREFIX):
            monkeypatch.delenv(variable)
    state_directory = tmp_path / "state"
    monkeypatch.setenv(f"{ENVIRONMENT_PREFIX}STATE_DIRECTORY", str(state_directory))
    monkeypatch.setenv(
        f"{ENVIRONMENT_PREFIX}DOWNLOAD_DIRECTORY", str(tmp_path / "downloads")
    )
    return state_directory


@pytest.fixture
def read_stored_job(state_directory: Path) -> Iterator[Callable[[int], Job]]:
    """Función que lee un job de la base de datos que dejaron los comandos."""
    opened_connections = []

    def read(job_id: int) -> Job:
        connection = open_database(state_directory / "queue.sqlite3")
        opened_connections.append(connection)
        return SqliteJobStore(connection).get(JobId(job_id))

    yield read
    for connection in opened_connections:
        connection.close()
