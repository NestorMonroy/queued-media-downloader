from dataclasses import replace
from pathlib import Path

import pytest

from queued_media_downloader.job_queue import RetryJob
from queued_media_downloader.job_storage import JobNotFoundError
from queued_media_downloader.jobs import (
    DownloadOptions,
    Job,
    JobId,
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


def store_jobs(job_store: InMemoryJobStore, *statuses: JobStatus) -> list[JobId]:
    job_ids = []
    for number, status in enumerate(statuses):
        job_id = job_store.create(
            Job.new_expansion(f"https://media.example/{number}", DOWNLOAD_OPTIONS)
        )
        job_store.update(replace(job_store.get(job_id), status=status))
        job_ids.append(job_id)
    return job_ids


def retried_job_ids(inbox: InMemoryJobRequestInbox) -> list[int]:
    requests = inbox.all_requests()
    assert {request.request_type for request in requests} <= {JobRequestType.RETRY}
    return [request.job_id for request in requests]


def test_failed_and_cancelled_jobs_are_requested_others_are_reported() -> None:
    job_store = InMemoryJobStore()
    failed, cancelled, completed, skipped, pending = store_jobs(
        job_store,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        JobStatus.COMPLETED,
        JobStatus.SKIPPED,
        JobStatus.PENDING,
    )
    inbox = InMemoryJobRequestInbox(job_store)

    result = RetryJob(job_store, inbox).execute(
        [failed, cancelled, completed, skipped, pending]
    )

    assert retried_job_ids(inbox) == [failed, cancelled]
    assert [job.job_id for job in result.not_retriable] == [completed, skipped, pending]
    assert job_store.get(failed).status is JobStatus.FAILED


def test_all_failed_requests_every_failed_job_and_nothing_else() -> None:
    job_store = InMemoryJobStore()
    first, _, second = store_jobs(
        job_store, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.FAILED
    )
    inbox = InMemoryJobRequestInbox(job_store)

    RetryJob(job_store, inbox).execute_all_failed()

    assert retried_job_ids(inbox) == [first, second]


def test_missing_job_registers_nothing() -> None:
    job_store = InMemoryJobStore()
    [failed] = store_jobs(job_store, JobStatus.FAILED)
    inbox = InMemoryJobRequestInbox(job_store)

    with pytest.raises(JobNotFoundError):
        RetryJob(job_store, inbox).execute([failed, JobId(99)])

    assert inbox.all_requests() == []
