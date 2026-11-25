from dataclasses import replace
from pathlib import Path

import pytest

from queued_media_downloader.job_queue import ListJobs, ShowJob
from queued_media_downloader.job_storage import JobNotFoundError
from queued_media_downloader.jobs import (
    DownloadOptions,
    Job,
    JobId,
    JobKind,
    JobStatus,
)
from tests.doubles.in_memory_job_store import InMemoryJobStore

DOWNLOAD_OPTIONS = DownloadOptions(
    format_selector="b",
    download_directory=Path("downloads"),
    output_template="%(id)s.%(ext)s",
    audio_only=False,
)


def store(
    job_store: InMemoryJobStore,
    status: JobStatus,
    *,
    parent_id: int | None = None,
    kind: JobKind = JobKind.DOWNLOAD,
) -> JobId:
    job_id = job_store.create(
        replace(
            Job.new_expansion("https://media.example/x", DOWNLOAD_OPTIONS),
            kind=kind,
            parent_id=None if parent_id is None else JobId(parent_id),
        )
    )
    job_store.update(replace(job_store.get(job_id), status=status))
    return job_id


@pytest.fixture
def playlist_store() -> InMemoryJobStore:
    """Una playlist (1) con tres hijos y un contenido suelto (5)."""
    job_store = InMemoryJobStore()
    store(job_store, JobStatus.COMPLETED, kind=JobKind.EXPANSION)
    store(job_store, JobStatus.COMPLETED, parent_id=1)
    store(job_store, JobStatus.FAILED, parent_id=1)
    store(job_store, JobStatus.COMPLETED, parent_id=1)
    store(job_store, JobStatus.FAILED)
    return job_store


def ids(jobs: list[Job]) -> list[int]:
    return [job.job_id for job in jobs if job.job_id is not None]


def test_list_shows_every_job_without_filters(playlist_store: InMemoryJobStore) -> None:
    assert ids(ListJobs(playlist_store).execute()) == [1, 2, 3, 4, 5]


def test_list_filters_by_status_and_by_parent(playlist_store: InMemoryJobStore) -> None:
    list_jobs = ListJobs(playlist_store)

    assert ids(list_jobs.execute(status=JobStatus.FAILED)) == [3, 5]
    assert ids(list_jobs.execute(parent_id=JobId(1))) == [2, 3, 4]
    assert ids(list_jobs.execute(JobStatus.FAILED, JobId(1))) == [3]


def test_list_of_a_missing_parent_is_an_error(playlist_store: InMemoryJobStore) -> None:
    with pytest.raises(JobNotFoundError):
        ListJobs(playlist_store).execute(parent_id=JobId(99))


def test_show_of_a_playlist_summarises_its_children_by_status(
    playlist_store: InMemoryJobStore,
) -> None:
    details = ShowJob(playlist_store).execute(JobId(1))

    assert details.job.job_id == JobId(1)
    assert details.children_by_status == {JobStatus.COMPLETED: 2, JobStatus.FAILED: 1}


def test_show_of_a_download_has_no_children_summary(
    playlist_store: InMemoryJobStore,
) -> None:
    assert ShowJob(playlist_store).execute(JobId(5)).children_by_status == {}
