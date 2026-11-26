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


@pytest.mark.parametrize(
    ("command", "status"),
    [
        (["cancel", "1"], "PENDING"),
        (["retry", "1"], "FAILED"),
        (["purge"], "CANCELLED"),
    ],
    ids=["cancel", "retry", "purge"],
)
def test_every_writing_command_reports_a_busy_queue_without_changing_it(
    state_directory: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
    status: str,
) -> None:
    # Otro proceso escribe (por ejemplo, run): en WAL se puede leer, no escribir.
    main(["enqueue", "https://media.example/watch?v=first"])
    database_path = state_directory / "queue.sqlite3"
    setup = sqlite3.connect(database_path)
    with setup:
        setup.execute("UPDATE jobs SET status = ?", (status,))
    before = setup.execute("SELECT * FROM jobs").fetchall()
    setup.close()
    partial_file = (
        state_directory.parent / "downloads" / ".partial" / "job-1" / "a.part"
    )
    partial_file.parent.mkdir(parents=True)
    partial_file.write_bytes(b"kept for a retry")
    monkeypatch.setattr(
        sqlite_connection,
        "CONNECTION_PRAGMAS",
        tuple(
            "PRAGMA busy_timeout = 200" if "busy_timeout" in pragma else pragma
            for pragma in sqlite_connection.CONNECTION_PRAGMAS
        ),
    )
    other_process = sqlite3.connect(database_path)
    other_process.execute("BEGIN IMMEDIATE")
    capsys.readouterr()

    try:
        exit_code = main(command)
    finally:
        other_process.rollback()
        other_process.close()

    after_connection = sqlite3.connect(database_path)
    after = after_connection.execute("SELECT * FROM jobs").fetchall()
    request_count = after_connection.execute(
        "SELECT count(*) FROM job_requests"
    ).fetchone()[0]
    after_connection.close()
    assert exit_code == 1
    assert "the queue is busy" in capsys.readouterr().err
    assert after == before
    assert request_count == 0
    assert partial_file.read_bytes() == b"kept for a retry"
