import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_migrations import (
    LATEST_SCHEMA_VERSION,
)


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
