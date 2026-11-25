"""JobEventApplier mientras un job se está cancelando (UC-05 A3, T37)."""

from dataclasses import replace
from pathlib import Path

import pytest

from queued_media_downloader.job_queue.job_event_applier import JobEventApplier
from queued_media_downloader.jobs import (
    DownloadOptions,
    FailureReason,
    Job,
    JobCancelled,
    JobCompleted,
    JobEvent,
    JobFailed,
    JobId,
    JobKind,
    JobStatus,
    MediaKey,
    PlaylistEntriesFound,
    PlaylistEntry,
    SingleMediaFound,
)
from queued_media_downloader.workers import WorkerMessage
from tests.doubles.in_memory_job_store import InMemoryJobStore

DOWNLOAD_OPTIONS = DownloadOptions(
    format_selector="b",
    download_directory=Path("downloads"),
    output_template="%(id)s.%(ext)s",
    audio_only=False,
)
ENTRY = PlaylistEntry(
    url="https://media.example/watch?v=b",
    playlist_index=1,
    kind=JobKind.DOWNLOAD,
    title="B",
    media_key=MediaKey(extractor_key="Example", media_id="b"),
    is_available=True,
)


def store_cancelling_job(job_store: InMemoryJobStore, kind: JobKind) -> JobId:
    job_id = job_store.create(
        Job.new_expansion("https://media.example/x", DOWNLOAD_OPTIONS)
    )
    job_store.update(
        replace(
            job_store.get(job_id), kind=kind, status=JobStatus.CANCELLATION_REQUESTED
        )
    )
    return job_id


def message(job_id: JobId, job_event: JobEvent) -> WorkerMessage:
    return WorkerMessage(
        worker_id=1, job_id=job_id, sequence_number=2, job_event=job_event
    )


def test_completion_wins_over_a_requested_cancellation() -> None:
    # A3: el job terminó antes de ver la bandera.
    job_store = InMemoryJobStore()
    job_id = store_cancelling_job(job_store, JobKind.DOWNLOAD)

    JobEventApplier(job_store).apply(message(job_id, JobCompleted(output_path="a.mp4")))

    assert job_store.get(job_id).status is JobStatus.COMPLETED


@pytest.mark.parametrize(
    ("kind", "job_event"),
    [
        (JobKind.DOWNLOAD, JobCancelled()),
        (
            JobKind.DOWNLOAD,
            JobFailed(failure_reason=FailureReason.NETWORK, failure_message="Reset"),
        ),
        (
            JobKind.DOWNLOAD,
            JobFailed(
                failure_reason=FailureReason.WORKER_CRASHED, failure_message="Crashed"
            ),
        ),
        (
            JobKind.EXPANSION,
            SingleMediaFound(
                media_key=MediaKey(extractor_key="Example", media_id="a"), title="A"
            ),
        ),
    ],
    ids=["confirmed", "failed meanwhile", "worker crashed", "single media found"],
)
def test_any_other_end_of_a_cancelling_job_confirms_the_cancellation(
    kind: JobKind, job_event: JobEvent
) -> None:
    job_store = InMemoryJobStore()
    job_id = store_cancelling_job(job_store, kind)

    JobEventApplier(job_store).apply(message(job_id, job_event))

    assert job_store.get(job_id).status is JobStatus.CANCELLED


def test_batch_of_a_cancelling_expansion_creates_no_children() -> None:
    job_store = InMemoryJobStore()
    job_id = store_cancelling_job(job_store, JobKind.EXPANSION)
    batch = PlaylistEntriesFound(
        playlist_id="PL1", playlist_title="L", playlist_entries=(ENTRY,)
    )

    JobEventApplier(job_store).apply(message(job_id, batch))

    assert job_store.get_children(job_id) == []


@pytest.mark.parametrize(
    "job_event",
    [
        JobCompleted(output_path="a.mp4"),
        JobCancelled(),
        JobFailed(failure_reason=FailureReason.NETWORK, failure_message="Reset"),
    ],
    ids=["completed", "cancelled", "failed"],
)
def test_late_event_of_a_job_already_finished_is_ignored(job_event: JobEvent) -> None:
    # Tras una terminación forzada aún puede llegar lo que el worker envió antes.
    job_store = InMemoryJobStore()
    job_id = store_cancelling_job(job_store, JobKind.DOWNLOAD)
    job_store.update(job_store.get(job_id).confirm_cancellation())

    updated_job = JobEventApplier(job_store).apply(message(job_id, job_event))

    assert updated_job is None
    assert job_store.get(job_id).status is JobStatus.CANCELLED
