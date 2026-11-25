from collections.abc import Callable
from pathlib import Path

import pytest

from queued_media_downloader.command_line.command_parser import main
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_request_inbox import (
    SqliteJobRequestInbox,
)
from queued_media_downloader.jobs import Job, JobRequestType, JobStatus


def unprocessed_requests(state_directory: Path) -> list[tuple[int, JobRequestType]]:
    connection = open_database(state_directory / "queue.sqlite3")
    try:
        requests = SqliteJobRequestInbox(connection).get_unprocessed()
    finally:
        connection.close()
    return [(request.job_id, request.request_type) for request in requests]


def test_cancel_registers_a_request_without_run_and_exits_with_0(
    state_directory: Path,
    read_stored_job: Callable[[int], Job],
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A5: sin run activo, la petición queda registrada para el siguiente run.
    main(["enqueue", "https://media.example/watch?v=a"])

    exit_code = main(["cancel", "1"])

    assert exit_code == 0
    assert unprocessed_requests(state_directory) == [(1, JobRequestType.CANCEL)]
    assert read_stored_job(1).status is JobStatus.PENDING
    assert "Cancellation requested for job 1" in capsys.readouterr().out


def test_cancel_of_a_missing_job_is_a_usage_error_and_registers_nothing(
    state_directory: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["enqueue", "https://media.example/watch?v=a"])

    exit_code = main(["cancel", "1", "99"])

    assert exit_code == 2
    assert unprocessed_requests(state_directory) == []
    assert "Job 99 does not exist" in capsys.readouterr().err


def test_cancel_of_a_finished_job_says_there_is_nothing_to_cancel(
    local_media_server: str,
    state_directory: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A7.
    main(["enqueue", f"{local_media_server}/sample.mp4"])
    main(["run"])
    capsys.readouterr()

    exit_code = main(["cancel", "1"])

    assert exit_code == 0
    assert unprocessed_requests(state_directory) == []
    assert "Job 1 already finished (COMPLETED); nothing to cancel" in (
        capsys.readouterr().out
    )
