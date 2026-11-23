from collections.abc import Iterator
from pathlib import Path

import pytest

from queued_media_downloader.job_queue import EnqueueMedia, InvalidUrlError
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_store import SqliteJobStore
from queued_media_downloader.jobs import DownloadOptions, JobKind, JobStatus

DOWNLOAD_OPTIONS = DownloadOptions(
    format_selector="bv*+ba/b",
    download_directory=Path("downloads"),
    output_template="%(title)s [%(id)s].%(ext)s",
    audio_only=False,
)


@pytest.fixture
def job_store(tmp_path: Path) -> Iterator[SqliteJobStore]:
    connection = open_database(tmp_path / "queue.sqlite3")
    yield SqliteJobStore(connection)
    connection.close()


def test_url_becomes_pending_expansion_job_with_its_options(
    job_store: SqliteJobStore,
) -> None:
    [job_id] = EnqueueMedia(job_store).execute(
        ["https://example.com/watch?v=1"], DOWNLOAD_OPTIONS
    )

    job = job_store.get(job_id)
    assert job.kind is JobKind.EXPANSION
    assert job.status is JobStatus.PENDING
    assert job.url == "https://example.com/watch?v=1"
    assert job.download_options == DOWNLOAD_OPTIONS


def test_each_url_becomes_one_job_in_the_given_order(
    job_store: SqliteJobStore,
) -> None:
    urls = ["https://example.com/a", "http://example.com/b", "https://example.org/c"]

    job_ids = EnqueueMedia(job_store).execute(urls, DOWNLOAD_OPTIONS)

    assert [job_store.get(job_id).url for job_id in job_ids] == urls
    assert len(job_store.get_next_pending(limit=10)) == 3


@pytest.mark.parametrize(
    "invalid_url",
    ["not a url", "example.com/watch", "ftp://example.com/file", "https://", ""],
)
def test_invalid_url_is_named_and_no_job_of_the_invocation_is_created(
    job_store: SqliteJobStore, invalid_url: str
) -> None:
    urls = ["https://example.com/valid", invalid_url, "https://example.com/other"]

    with pytest.raises(InvalidUrlError) as raised:
        EnqueueMedia(job_store).execute(urls, DOWNLOAD_OPTIONS)

    assert raised.value.url == invalid_url
    assert repr(invalid_url) in str(raised.value)
    assert job_store.get_next_pending(limit=10) == []
