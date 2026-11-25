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

    assert schema_version == LATEST_SCHEMA_VERSION
    assert job_count == 2


def database_at_version_2(database_path: Path) -> sqlite3.Connection:
    """Base de datos con las migraciones 1 y 2, como la dejó E1."""
    connection = sqlite3.connect(database_path)
    version_2_scripts = "\n".join(m.script for m in load_migrations()[:2])
    connection.executescript(f"{version_2_scripts}\nPRAGMA user_version = 2;")
    return connection


def test_migration_3_keeps_jobs_their_links_and_their_requests(tmp_path: Path) -> None:
    database_path = tmp_path / "queue.sqlite3"
    version_2 = database_at_version_2(database_path)
    version_2.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    version_2.execute(INSERT_DOWNLOAD, ("Youtube", "def", '{"audio_only": false}'))
    version_2.execute("UPDATE jobs SET parent_id = 1 WHERE id = 2")
    version_2.execute(
        "INSERT INTO job_requests (job_id, request_type, requested_at)"
        " VALUES (2, 'CANCEL', '2026-11-25T00:00:00+00:00')"
    )
    version_2.commit()
    version_2.close()

    migrated = open_database(database_path)
    jobs = migrated.execute("SELECT id, parent_id, media_id FROM jobs").fetchall()
    requests = migrated.execute("SELECT job_id, request_type FROM job_requests")
    foreign_key_problems = migrated.execute("PRAGMA foreign_key_check").fetchall()
    schema_version = pragma(migrated, "user_version")
    request_rows = requests.fetchall()
    migrated.close()

    assert schema_version == 3
    assert jobs == [(1, None, "abc"), (2, 1, "def")]
    assert request_rows == [(2, "CANCEL")]
    assert foreign_key_problems == []


def test_job_ids_are_never_reused_after_deleting_the_last_job(tmp_path: Path) -> None:
    # La carpeta de parciales lleva el id del job (T44): un id reutilizado
    # heredaría los parciales de un job borrado.
    database_path = tmp_path / "queue.sqlite3"
    version_2 = database_at_version_2(database_path)
    version_2.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    version_2.execute(INSERT_DOWNLOAD, ("Youtube", "def", '{"audio_only": false}'))
    version_2.commit()
    version_2.close()
    migrated = open_database(database_path)

    migrated.execute("DELETE FROM jobs WHERE id = 2")
    cursor = migrated.execute(
        INSERT_DOWNLOAD, ("Youtube", "ghi", '{"audio_only": false}')
    )
    new_job_id = cursor.lastrowid
    migrated.close()

    assert new_job_id == 3


def test_deleting_a_job_still_deletes_its_children_and_requests(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    connection.execute(INSERT_DOWNLOAD, ("Youtube", "def", '{"audio_only": false}'))
    connection.execute("UPDATE jobs SET parent_id = 1 WHERE id = 2")
    connection.execute(
        "INSERT INTO job_requests (job_id, request_type, requested_at)"
        " VALUES (2, 'CANCEL', '2026-11-25T00:00:00+00:00')"
    )

    connection.execute("DELETE FROM jobs WHERE id = 1")

    assert connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 0
    assert connection.execute("SELECT count(*) FROM job_requests").fetchone()[0] == 0


def test_two_jobs_cannot_own_the_same_output_file(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    connection.execute(INSERT_DOWNLOAD, ("Youtube", "def", '{"audio_only": false}'))
    connection.execute(
        "UPDATE jobs SET output_path = 'downloads/video.mp4' WHERE id = 1"
    )

    with pytest.raises(sqlite3.IntegrityError, match=r"jobs\.output_path"):
        connection.execute(
            "UPDATE jobs SET output_path = 'downloads/video.mp4' WHERE id = 2"
        )
