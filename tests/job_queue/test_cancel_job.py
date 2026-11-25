from dataclasses import replace
from pathlib import Path

import pytest

from queued_media_downloader.job_queue import CancelJob
from queued_media_downloader.job_storage import JobNotFoundError
from queued_media_downloader.jobs import (
    DownloadOptions,
    Job,
    JobId,
    JobKind,
    JobRequestType,
    JobStatus,
)
from tests.doubles.in_memory_job_request_inbox import InMemoryJobRequestInbox
from tests.doubles.in_memory_job_store import InMemoryJobStore

DOWNLOAD_OPTIONS = DownloadOptions(
    format_selector="b",
    download_directory=Path("downloads"),
    output_template="%(id)s.%(ext)s",
    audio_only=False,
)


def store_job(
    job_store: InMemoryJobStore,
    *,
    status: JobStatus = JobStatus.PENDING,
    parent_id: int | None = None,
    kind: JobKind = JobKind.EXPANSION,
) -> JobId:
    """Guarda un job con el estado y el padre indicados."""
    job = replace(
        Job.new_expansion("https://media.example/x", DOWNLOAD_OPTIONS),
        kind=kind,
        parent_id=None if parent_id is None else JobId(parent_id),
    )
    job_id = job_store.create(job)
    job_store.update(replace(job_store.get(job_id), status=status))
    return job_id


def cancelled_job_ids(inbox: InMemoryJobRequestInbox) -> list[int]:
    requests = inbox.all_requests()
    assert {request.request_type for request in requests} <= {JobRequestType.CANCEL}
    return [request.job_id for request in requests]


def test_cancelling_registers_a_request_and_changes_no_state() -> None:
    job_store = InMemoryJobStore()
    pending = store_job(job_store)
    running = store_job(job_store, status=JobStatus.RUNNING)
    inbox = InMemoryJobRequestInbox(job_store)

    result = CancelJob(job_store, inbox).execute([pending, running])

    assert cancelled_job_ids(inbox) == [pending, running]
    assert result.requested == {pending: 0, running: 0}
    assert job_store.get(pending).status is JobStatus.PENDING
    assert job_store.get(running).status is JobStatus.RUNNING


@pytest.mark.parametrize(
    "status",
    [JobStatus.COMPLETED, JobStatus.SKIPPED, JobStatus.CANCELLED, JobStatus.FAILED],
)
def test_finished_job_is_reported_and_not_requested(status: JobStatus) -> None:
    # A7: no hay nada que cancelar.
    job_store = InMemoryJobStore()
    finished = store_job(job_store, status=status)
    inbox = InMemoryJobRequestInbox(job_store)

    result = CancelJob(job_store, inbox).execute([finished])

    assert inbox.all_requests() == []
    assert [job.job_id for job in result.already_finished] == [finished]


def test_cancelling_a_playlist_requests_its_unfinished_descendants() -> None:
    # A4, también con una playlist anidada.
    job_store = InMemoryJobStore()
    playlist = store_job(job_store, status=JobStatus.COMPLETED)
    expansion = store_job(job_store, status=JobStatus.RUNNING)
    done = store_job(
        job_store,
        parent_id=expansion,
        kind=JobKind.DOWNLOAD,
        status=JobStatus.COMPLETED,
    )
    pending = store_job(job_store, parent_id=expansion, kind=JobKind.DOWNLOAD)
    nested = store_job(job_store, parent_id=expansion)
    nested_child = store_job(job_store, parent_id=nested, kind=JobKind.DOWNLOAD)
    inbox = InMemoryJobRequestInbox(job_store)

    result = CancelJob(job_store, inbox).execute([expansion])

    assert cancelled_job_ids(inbox) == [expansion, pending, nested, nested_child]
    assert done not in cancelled_job_ids(inbox)
    assert playlist not in cancelled_job_ids(inbox)
    assert result.requested == {expansion: 3}


def test_job_named_twice_or_also_as_a_descendant_is_requested_once() -> None:
    job_store = InMemoryJobStore()
    expansion = store_job(job_store, status=JobStatus.RUNNING)
    child = store_job(job_store, parent_id=expansion, kind=JobKind.DOWNLOAD)
    inbox = InMemoryJobRequestInbox(job_store)

    CancelJob(job_store, inbox).execute([expansion, child, expansion])

    assert cancelled_job_ids(inbox) == [expansion, child]


def test_missing_job_registers_nothing() -> None:
    job_store = InMemoryJobStore()
    existing = store_job(job_store)
    inbox = InMemoryJobRequestInbox(job_store)

    with pytest.raises(JobNotFoundError):
        CancelJob(job_store, inbox).execute([existing, JobId(99)])

    assert inbox.all_requests() == []
