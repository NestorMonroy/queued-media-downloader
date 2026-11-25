"""enqueue con la base de datos bloqueada por otro proceso (UC-02 A3)."""

import sqlite3
from pathlib import Path

import pytest

from queued_media_downloader.command_line.command_parser import main
from queued_media_downloader.job_storage import sqlite_connection


def test_locked_database_queues_nothing_and_exits_with_1(
    state_directory: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main(["enqueue", "https://media.example/watch?v=first"])
    monkeypatch.setattr(
        sqlite_connection,
        "CONNECTION_PRAGMAS",
        tuple(
            "PRAGMA busy_timeout = 200" if "busy_timeout" in pragma else pragma
            for pragma in sqlite_connection.CONNECTION_PRAGMAS
        ),
    )
    other_process = sqlite3.connect(state_directory / "queue.sqlite3")
    other_process.execute("BEGIN IMMEDIATE")
    capsys.readouterr()

    try:
        exit_code = main(
            ["enqueue", "https://media.example/watch?v=a", "https://media.example/b"]
        )
    finally:
        other_process.rollback()
        other_process.close()

    job_count = (
        sqlite3.connect(state_directory / "queue.sqlite3")
        .execute("SELECT count(*) FROM jobs")
        .fetchone()[0]
    )
    assert exit_code == 1
    assert job_count == 1
    assert "the queue is busy" in capsys.readouterr().err
