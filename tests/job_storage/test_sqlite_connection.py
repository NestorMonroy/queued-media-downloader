import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_migrations import (
    LATEST_SCHEMA_VERSION,
    load_migrations,
)

# Descarga activa mínima, con las columnas obligatorias de la versión 1.
INSERT_DOWNLOAD = """
    INSERT INTO jobs (kind, status, url, extractor_key, media_id,
                      download_options, attempt_count, created_at, updated_at)
    VALUES ('DOWNLOAD', 'PENDING', 'https://media.example/abc', ?, ?, ?, 0,
            '2026-11-23T00:00:00+00:00', '2026-11-23T00:00:00+00:00')
"""


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    database_connection = open_database(tmp_path / "queue.sqlite3")
    yield database_connection
    database_connection.close()


def pragma(connection: sqlite3.Connection, name: str) -> object:
    row = connection.execute(f"PRAGMA {name}").fetchone()
    return row[0]


def test_opening_a_new_database_applies_every_migration(
    connection: sqlite3.Connection,
) -> None:
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    assert pragma(connection, "user_version") == LATEST_SCHEMA_VERSION
    assert {"jobs", "job_requests"} <= tables


def test_reopening_a_database_does_not_reapply_migrations(tmp_path: Path) -> None:
    database_path = tmp_path / "queue.sqlite3"
    open_database(database_path).close()

    reopened_connection = open_database(database_path)
    schema_version = pragma(reopened_connection, "user_version")
    reopened_connection.close()

    assert schema_version == LATEST_SCHEMA_VERSION


@pytest.mark.parametrize(
    ("name", "expected_value"),
    [
        ("journal_mode", "wal"),
        ("foreign_keys", 1),
        ("busy_timeout", 5000),
        ("synchronous", 1),
    ],
    ids=["write-ahead log", "foreign keys", "busy timeout", "synchronous normal"],
)
def test_connection_applies_the_designed_pragmas(
    connection: sqlite3.Connection, name: str, expected_value: object
) -> None:
    assert pragma(connection, name) == expected_value


def test_migration_2_keeps_jobs_and_tells_duplicates_by_output_kind(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "queue.sqlite3"
    version_1 = sqlite3.connect(database_path)
    version_1.executescript(f"{load_migrations()[0].script}\nPRAGMA user_version = 1;")
    version_1.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    version_1.commit()
    version_1.close()

    migrated = open_database(database_path)
    migrated.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": true}'))
    with pytest.raises(sqlite3.IntegrityError):
        migrated.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    job_count = migrated.execute("SELECT count(*) FROM jobs").fetchone()[0]
    schema_version = pragma(migrated, "user_version")
    migrated.close()

    assert schema_version == 2
    assert job_count == 2
