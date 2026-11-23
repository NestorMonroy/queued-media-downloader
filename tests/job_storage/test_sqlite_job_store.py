import sqlite3
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from queued_media_downloader.job_storage import (
    DuplicateActiveDownloadError,
    JobNotFoundError,
)
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_store import SqliteJobStore
from queued_media_downloader.jobs import (
    DownloadOptions,
    FailureReason,
    Job,
    JobId,
    JobKind,
    JobStatus,
    MediaKey,
    PlaylistContext,
)

MEDIA_KEY = MediaKey(extractor_key="Youtube", media_id="abc123")


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "queue.sqlite3"


@pytest.fixture
def connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    database_connection = open_database(database_path)
    yield database_connection
    database_connection.close()


@pytest.fixture
def job_store(connection: sqlite3.Connection) -> SqliteJobStore:
    return SqliteJobStore(connection)


def make_job(url: str = "https://media.example/watch?v=abc123") -> Job:
    download_options = DownloadOptions(
        format_selector="bv*+ba/b",
        download_directory=Path("downloads"),
        output_template="%(title)s [%(id)s].%(ext)s",
        audio_only=True,
    )
    return Job.new_expansion(url, download_options)


def make_download(
    job_store: SqliteJobStore, status: JobStatus, *, audio_only: bool = True
) -> Job:
    stored_job = job_store.get(job_store.create(make_job()))
    download_options = replace(stored_job.download_options, audio_only=audio_only)
    return replace(
        stored_job,
        kind=JobKind.DOWNLOAD,
        status=status,
        media_key=MEDIA_KEY,
        download_options=download_options,
    )


def test_created_job_reads_back_equal_with_its_assigned_id(
    job_store: SqliteJobStore,
) -> None:
    new_job = make_job()

    job_id = job_store.create(new_job)

    assert job_store.get(job_id) == replace(new_job, job_id=job_id)


def test_playlist_child_reads_back_with_its_parent_and_context(
    job_store: SqliteJobStore,
) -> None:
    parent_id = job_store.create(make_job())
    child = replace(
        make_job("https://media.example/watch?v=entry3"),
        kind=JobKind.DOWNLOAD,
        parent_id=parent_id,
        playlist_context=PlaylistContext(
            playlist_id="PL123",
            playlist_title="Favorites",
            playlist_index=3,
            playlist_entry_count=None,
        ),
    )

    child_id = job_store.create(child)

    assert job_store.get(child_id) == replace(child, job_id=child_id)


def test_job_without_playlist_has_no_parent_nor_context(
    job_store: SqliteJobStore,
) -> None:
    job = job_store.get(job_store.create(make_job()))

    assert job.parent_id is None
    assert job.playlist_context is None


def test_batch_is_created_in_order_in_one_transaction(
    job_store: SqliteJobStore,
) -> None:
    urls = [f"https://media.example/watch?v={index}" for index in range(3)]

    job_ids = job_store.create_many([make_job(url) for url in urls])

    assert [job_store.get(job_id).url for job_id in job_ids] == urls
    assert job_ids == sorted(job_ids)


def test_batch_with_a_duplicate_download_stores_none_of_its_jobs(
    job_store: SqliteJobStore,
) -> None:
    job_store.update(make_download(job_store, JobStatus.PENDING))
    jobs_before = len(job_store.get_next_pending(limit=100))
    new_job = make_job("https://media.example/watch?v=new")
    duplicate = replace(make_job(), kind=JobKind.DOWNLOAD, media_key=MEDIA_KEY)

    with pytest.raises(DuplicateActiveDownloadError):
        job_store.create_many([new_job, duplicate])

    assert len(job_store.get_next_pending(limit=100)) == jobs_before


def test_whole_playlist_option_is_stored_with_the_job(
    job_store: SqliteJobStore,
) -> None:
    job = make_job()
    job = replace(
        job, download_options=replace(job.download_options, whole_playlist=True)
    )

    stored = job_store.get(job_store.create(job))

    assert stored.download_options.whole_playlist is True


def test_jobs_stored_before_the_playlist_option_read_it_as_false(
    job_store: SqliteJobStore, database_path: Path
) -> None:
    job_id = job_store.create(make_job())
    connection = sqlite3.connect(database_path)
    connection.execute(
        "UPDATE jobs SET download_options = json_remove(download_options, "
        "'$.whole_playlist') WHERE id = ?",
        (job_id,),
    )
    connection.commit()
    connection.close()

    assert job_store.get(job_id).download_options.whole_playlist is False


def test_created_jobs_receive_increasing_ids(job_store: SqliteJobStore) -> None:
    first_id = job_store.create(make_job())
    second_id = job_store.create(make_job())

    assert second_id > first_id


def test_update_persists_every_field_of_the_job(job_store: SqliteJobStore) -> None:
    stored_job = job_store.get(job_store.create(make_job()))
    changed_job = replace(
        stored_job,
        kind=JobKind.DOWNLOAD,
        status=JobStatus.FAILED,
        media_key=MEDIA_KEY,
        title="A video",
        selected_format_id="137+140",
        attempt_count=2,
        failure_reason=FailureReason.NETWORK,
        failure_message="Connection reset",
        output_path="downloads/A video [abc123].mp4",
    )

    job_store.update(changed_job)

    assert job_store.get(changed_job.job_id or JobId(0)) == changed_job


def test_getting_a_missing_job_raises_job_not_found(job_store: SqliteJobStore) -> None:
    with pytest.raises(JobNotFoundError):
        job_store.get(JobId(999))


def test_updating_a_missing_job_raises_job_not_found(job_store: SqliteJobStore) -> None:
    with pytest.raises(JobNotFoundError):
        job_store.update(replace(make_job(), job_id=JobId(999)))


def test_updating_a_job_that_was_never_stored_is_rejected(
    job_store: SqliteJobStore,
) -> None:
    with pytest.raises(ValueError, match="stored"):
        job_store.update(make_job())


def test_next_pending_jobs_come_in_creation_order_up_to_the_limit(
    job_store: SqliteJobStore,
) -> None:
    first_id = job_store.create(make_job("https://media.example/1"))
    running_id = job_store.create(make_job("https://media.example/2"))
    third_id = job_store.create(make_job("https://media.example/3"))
    job_store.create(make_job("https://media.example/4"))
    job_store.update(job_store.get(running_id).transition_to(JobStatus.RUNNING))

    next_pending = job_store.get_next_pending(limit=2)

    assert [job.job_id for job in next_pending] == [first_id, third_id]


def test_jobs_with_the_given_statuses_come_in_creation_order(
    job_store: SqliteJobStore,
) -> None:
    job_ids = [
        job_store.create(make_job(f"https://media.example/{n}")) for n in range(4)
    ]
    for job_id in (job_ids[3], job_ids[1]):
        job_store.update(job_store.get(job_id).transition_to(JobStatus.RUNNING))
    job_store.update(
        job_store.get(job_ids[1]).transition_to(JobStatus.CANCELLATION_REQUESTED)
    )

    found_jobs = job_store.get_with_status(
        {JobStatus.RUNNING, JobStatus.CANCELLATION_REQUESTED}
    )

    assert [(job.job_id, job.status) for job in found_jobs] == [
        (job_ids[1], JobStatus.CANCELLATION_REQUESTED),
        (job_ids[3], JobStatus.RUNNING),
    ]


def test_no_status_finds_no_jobs(job_store: SqliteJobStore) -> None:
    job_store.create(make_job())

    assert job_store.get_with_status(set()) == []


def test_active_download_is_detected_by_media_key(job_store: SqliteJobStore) -> None:
    job_store.update(make_download(job_store, JobStatus.PENDING))

    assert job_store.has_active_download(MEDIA_KEY, audio_only=True)
    assert not job_store.has_active_download(
        MediaKey("Youtube", "other"), audio_only=True
    )


def test_skipped_download_does_not_count_as_active(job_store: SqliteJobStore) -> None:
    job_store.update(make_download(job_store, JobStatus.SKIPPED))

    assert not job_store.has_active_download(MEDIA_KEY, audio_only=True)


def test_second_active_download_of_the_same_media_is_rejected(
    job_store: SqliteJobStore,
) -> None:
    job_store.update(make_download(job_store, JobStatus.PENDING))

    with pytest.raises(DuplicateActiveDownloadError):
        job_store.update(make_download(job_store, JobStatus.PENDING))


def test_active_download_is_detected_by_media_key_and_output_kind(
    job_store: SqliteJobStore,
) -> None:
    job_store.update(make_download(job_store, JobStatus.PENDING, audio_only=False))

    assert job_store.has_active_download(MEDIA_KEY, audio_only=False)
    assert not job_store.has_active_download(MEDIA_KEY, audio_only=True)


def test_same_media_can_be_downloaded_as_video_and_as_audio(
    job_store: SqliteJobStore,
) -> None:
    video_download = make_download(job_store, JobStatus.PENDING, audio_only=False)
    audio_download = make_download(job_store, JobStatus.PENDING, audio_only=True)

    job_store.update(video_download)
    job_store.update(audio_download)

    assert job_store.get(audio_download.job_id or JobId(0)) == audio_download


def test_duplicate_download_can_be_stored_as_skipped(
    job_store: SqliteJobStore,
) -> None:
    job_store.update(make_download(job_store, JobStatus.PENDING))
    skipped_duplicate = make_download(job_store, JobStatus.SKIPPED)

    job_store.update(skipped_duplicate)

    assert job_store.get(skipped_duplicate.job_id or JobId(0)) == skipped_duplicate


def test_jobs_survive_closing_and_reopening_the_database(
    database_path: Path,
) -> None:
    first_connection = open_database(database_path)
    job_id = SqliteJobStore(first_connection).create(make_job())
    first_connection.close()

    second_connection = open_database(database_path)
    reopened_job = SqliteJobStore(second_connection).get(job_id)
    second_connection.close()

    assert reopened_job.job_id == job_id
