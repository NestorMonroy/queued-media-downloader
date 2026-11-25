import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from queued_media_downloader.job_storage import JobNotFoundError
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_request_inbox import (
    SqliteJobRequestInbox,
)
from queued_media_downloader.job_storage.sqlite_job_store import SqliteJobStore
from queued_media_downloader.jobs import (
    DownloadOptions,
    Job,
    JobId,
    JobRequest,
    JobRequestType,
)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    database_connection = open_database(tmp_path / "queue.sqlite3")
    yield database_connection
    database_connection.close()


def store_jobs(connection: sqlite3.Connection, count: int) -> list[JobId]:
    options = DownloadOptions(
        format_selector="b",
        download_directory=Path("downloads"),
        output_template="%(id)s.%(ext)s",
        audio_only=False,
    )
    job_store = SqliteJobStore(connection)
    return [
        job_store.create(Job.new_expansion(f"https://media.example/{n}", options))
        for n in range(count)
    ]


def cancel(job_id: JobId) -> JobRequest:
    return JobRequest(job_id=job_id, request_type=JobRequestType.CANCEL)


def test_requests_come_back_unprocessed_in_order(
    connection: sqlite3.Connection,
) -> None:
    first, second = store_jobs(connection, 2)
    inbox = SqliteJobRequestInbox(connection)

    request_ids = inbox.create_many([cancel(second), cancel(first)])

    assert inbox.get_unprocessed() == [
        JobRequest(
            request_id=request_ids[0], job_id=second, request_type=JobRequestType.CANCEL
        ),
        JobRequest(
            request_id=request_ids[1], job_id=first, request_type=JobRequestType.CANCEL
        ),
    ]


def test_processed_request_is_not_returned_again(
    connection: sqlite3.Connection,
) -> None:
    first, second = store_jobs(connection, 2)
    inbox = SqliteJobRequestInbox(connection)
    first_request_id, _ = inbox.create_many([cancel(first), cancel(second)])

    inbox.mark_processed(first_request_id)

    assert [request.job_id for request in inbox.get_unprocessed()] == [second]


def test_request_for_a_missing_job_stores_none_of_its_batch(
    connection: sqlite3.Connection,
) -> None:
    [existing] = store_jobs(connection, 1)
    inbox = SqliteJobRequestInbox(connection)

    with pytest.raises(JobNotFoundError):
        inbox.create_many([cancel(existing), cancel(JobId(99))])

    assert inbox.get_unprocessed() == []


def test_requests_survive_reopening_the_database(tmp_path: Path) -> None:
    # UC-05 A5: cancel registra la petición aunque run no esté activo.
    database_path = tmp_path / "queue.sqlite3"
    connection = open_database(database_path)
    [job_id] = store_jobs(connection, 1)
    SqliteJobRequestInbox(connection).create_many([cancel(job_id)])
    connection.close()

    reopened = open_database(database_path)
    unprocessed = SqliteJobRequestInbox(reopened).get_unprocessed()
    reopened.close()

    assert [request.job_id for request in unprocessed] == [job_id]
