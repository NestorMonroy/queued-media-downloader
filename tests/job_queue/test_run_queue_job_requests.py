"""RunQueue procesa las job requests de cancel (UC-05, T37)."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from queued_media_downloader.job_queue import RunQueue
from queued_media_downloader.jobs import (
    DownloadOptions,
    FormatSelected,
    Job,
    JobId,
    JobKind,
    JobRequest,
    JobRequestType,
    JobStatus,
    MediaKey,
    PlaylistEntriesFound,
    PlaylistEntry,
    SingleMediaFound,
)
from queued_media_downloader.workers import WorkerMessage
from tests.doubles.in_memory_job_request_inbox import InMemoryJobRequestInbox
from tests.doubles.in_memory_job_store import InMemoryJobStore
from tests.doubles.scripted_worker_pool import (
    WAIT_FOR_CANCELLATION,
    ScriptedWorkerPool,
    ScriptKey,
    ScriptStep,
)

URL = "https://media.example/watch?v=a"
PLAYLIST_URL = "https://media.example/playlist?list=PL1"
DOWNLOAD_OPTIONS = DownloadOptions(
    format_selector="b",
    download_directory=Path("downloads"),
    output_template="%(id)s.%(ext)s",
    audio_only=False,
)
FOUND_A = SingleMediaFound(
    media_key=MediaKey(extractor_key="Example", media_id="a"), title="A"
)


def cancel(job_id: int) -> JobRequest:
    return JobRequest(job_id=JobId(job_id), request_type=JobRequestType.CANCEL)


def queue_with(
    urls: Sequence[str],
    script: Mapping[ScriptKey, Sequence[ScriptStep]],
    *,
    ignores_cancellation: bool = False,
) -> tuple[InMemoryJobStore, InMemoryJobRequestInbox, ScriptedWorkerPool]:
    job_store = InMemoryJobStore()
    for url in urls:
        job_store.create(Job.new_expansion(url, DOWNLOAD_OPTIONS))
    inbox = InMemoryJobRequestInbox(job_store)
    pool = ScriptedWorkerPool(1, script, ignores_cancellation=ignores_cancellation)
    return job_store, inbox, pool


def test_pending_job_with_a_cancel_request_is_cancelled_without_running() -> None:
    # A1, y A5: la petición se registró sin run activo y se procesa al arrancar.
    job_store, inbox, pool = queue_with([URL], {})
    inbox.create_many([cancel(1)])

    RunQueue(job_store, pool, inbox).execute()

    assert job_store.get(JobId(1)).status is JobStatus.CANCELLED
    assert pool.submitted_jobs == []
    assert inbox.get_unprocessed() == []


def test_running_job_is_asked_to_stop_and_ends_cancelled() -> None:
    # Flujo básico: CANCELLATION_REQUESTED, petición al worker, JobCancelled.
    script: dict[ScriptKey, list[ScriptStep]] = {
        (JobKind.EXPANSION, URL): [FOUND_A],
        (JobKind.DOWNLOAD, URL): [
            FormatSelected(selected_format_id="18"),
            WAIT_FOR_CANCELLATION,
        ],
    }
    job_store, inbox, pool = queue_with([URL], script)

    def cancel_download_on_start(message: WorkerMessage, job: Job | None) -> None:
        del job
        if isinstance(message.job_event, FormatSelected):
            inbox.create_many([cancel(1)])

    run_result = RunQueue(
        job_store, pool, inbox, present=cancel_download_on_start
    ).execute()

    assert pool.cancellation_requests == [JobId(1)]
    assert job_store.get(JobId(1)).status is JobStatus.CANCELLED
    assert job_store.get(JobId(1)).selected_format_id == "18"
    assert inbox.get_unprocessed() == []
    assert run_result.failed_job_count == 0


def test_cancelling_an_expansion_cancels_children_created_meanwhile() -> None:
    # A4: los hijos creados tras registrar la petición también se cancelan, y
    # un lote que llega durante la cancelación ya no crea hijos.
    entry = PlaylistEntry(
        url="https://media.example/watch?v=b",
        playlist_index=1,
        kind=JobKind.DOWNLOAD,
        title="B",
        media_key=MediaKey(extractor_key="Example", media_id="b"),
        is_available=True,
    )
    batch = PlaylistEntriesFound(
        playlist_id="PL1", playlist_title="L", playlist_entries=(entry,)
    )
    script: dict[ScriptKey, list[ScriptStep]] = {
        (JobKind.EXPANSION, PLAYLIST_URL): [batch, WAIT_FOR_CANCELLATION],
    }
    job_store, inbox, pool = queue_with([PLAYLIST_URL], script)

    def cancel_after_first_batch(message: WorkerMessage, job: Job | None) -> None:
        del job
        if isinstance(message.job_event, PlaylistEntriesFound):
            inbox.create_many([cancel(1)])

    RunQueue(job_store, pool, inbox, present=cancel_after_first_batch).execute()

    expansion, child = job_store.all_jobs()
    assert expansion.status is JobStatus.CANCELLED
    assert child.parent_id == JobId(1)
    assert child.status is JobStatus.CANCELLED
    assert [job.kind for job in pool.submitted_jobs] == [JobKind.EXPANSION]


def test_request_for_a_job_that_already_finished_changes_nothing() -> None:
    # A7 dentro de run: el job terminó entre el registro y el procesamiento.
    job_store, inbox, pool = queue_with([URL], {})
    job_store.update(replace(job_store.get(JobId(1)), status=JobStatus.COMPLETED))
    inbox.create_many([cancel(1)])

    RunQueue(job_store, pool, inbox).execute()

    assert job_store.get(JobId(1)).status is JobStatus.COMPLETED
    assert inbox.get_unprocessed() == []


def test_retry_requests_are_left_for_the_retry_use_case() -> None:
    job_store, inbox, pool = queue_with([URL], {})
    job_store.update(replace(job_store.get(JobId(1)), status=JobStatus.FAILED))
    inbox.create_many([JobRequest(job_id=JobId(1), request_type=JobRequestType.RETRY)])

    RunQueue(job_store, pool, inbox).execute()

    assert [request.request_type for request in inbox.get_unprocessed()] == [
        JobRequestType.RETRY
    ]
