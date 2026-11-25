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


def test_worker_that_does_not_confirm_in_time_is_terminated() -> None:
    # A2: por ejemplo, mientras ffmpeg une archivos y no hay avances.
    script: dict[ScriptKey, list[ScriptStep]] = {
        (JobKind.EXPANSION, URL): [FOUND_A],
        (JobKind.DOWNLOAD, URL): [
            FormatSelected(selected_format_id="18"),
            WAIT_FOR_CANCELLATION,
        ],
    }
    job_store, inbox, pool = queue_with([URL], script, ignores_cancellation=True)

    def cancel_once_format_is_selected(message: WorkerMessage, job: Job | None) -> None:
        del job
        if isinstance(message.job_event, FormatSelected):
            inbox.create_many([cancel(1)])

    run_result = RunQueue(
        job_store,
        pool,
        inbox,
        present=cancel_once_format_is_selected,
        cancellation_grace_seconds=0.0,
    ).execute()

    assert pool.cancellation_requests == [JobId(1)]
    assert pool.terminated_job_ids == [JobId(1)]
    assert job_store.get(JobId(1)).status is JobStatus.CANCELLED
    assert run_result.failed_job_count == 0


def test_worker_that_confirms_in_time_is_not_terminated() -> None:
    script: dict[ScriptKey, list[ScriptStep]] = {
        (JobKind.EXPANSION, URL): [FOUND_A],
        (JobKind.DOWNLOAD, URL): [
            FormatSelected(selected_format_id="18"),
            WAIT_FOR_CANCELLATION,
        ],
    }
    job_store, inbox, pool = queue_with([URL], script)

    def cancel_once_format_is_selected(message: WorkerMessage, job: Job | None) -> None:
        del job
        if isinstance(message.job_event, FormatSelected):
            inbox.create_many([cancel(1)])

    RunQueue(
        job_store,
        pool,
        inbox,
        present=cancel_once_format_is_selected,
        cancellation_grace_seconds=60.0,
    ).execute()

    assert pool.terminated_job_ids == []
    assert job_store.get(JobId(1)).status is JobStatus.CANCELLED


class StopAfter:
    """stop_requested que se activa al presentar cierto job event (primer Ctrl+C)."""

    def __init__(self, event_type: type[object]) -> None:
        self._event_type = event_type
        self.requested = False

    def present(self, message: WorkerMessage, job: Job | None) -> None:
        del job
        if isinstance(message.job_event, self._event_type):
            self.requested = True

    def __call__(self) -> bool:
        return self.requested


def test_interruption_stops_running_jobs_and_leaves_them_recoverable() -> None:
    # A6: el primer Ctrl+C deja de enviar jobs y detiene los que están en curso
    # sin cancelarlos: siguen RUNNING y el siguiente run los recupera (UC-06).
    other_url = "https://media.example/watch?v=other"
    script: dict[ScriptKey, list[ScriptStep]] = {
        (JobKind.EXPANSION, URL): [FOUND_A],
        (JobKind.DOWNLOAD, URL): [
            FormatSelected(selected_format_id="18"),
            WAIT_FOR_CANCELLATION,
        ],
    }
    job_store, inbox, pool = queue_with([URL, other_url], script)
    stop = StopAfter(FormatSelected)

    run_result = RunQueue(
        job_store, pool, inbox, present=stop.present, stop_requested=stop
    ).execute()

    assert run_result.interrupted
    assert pool.cancellation_requests == [JobId(1)]
    assert job_store.get(JobId(1)).status is JobStatus.RUNNING
    assert job_store.get(JobId(2)).status is JobStatus.PENDING
    assert [job.job_id for job in pool.submitted_jobs] == [JobId(1), JobId(1)]


def test_interrupted_job_that_does_not_stop_in_time_is_terminated_still_running() -> (
    None
):
    script: dict[ScriptKey, list[ScriptStep]] = {
        (JobKind.EXPANSION, URL): [FOUND_A],
        (JobKind.DOWNLOAD, URL): [
            FormatSelected(selected_format_id="18"),
            WAIT_FOR_CANCELLATION,
        ],
    }
    job_store, inbox, pool = queue_with([URL], script, ignores_cancellation=True)
    stop = StopAfter(FormatSelected)

    run_result = RunQueue(
        job_store,
        pool,
        inbox,
        present=stop.present,
        stop_requested=stop,
        cancellation_grace_seconds=0.0,
    ).execute()

    assert run_result.interrupted
    assert pool.terminated_job_ids == [JobId(1)]
    assert job_store.get(JobId(1)).status is JobStatus.RUNNING


def test_run_that_is_not_interrupted_says_so() -> None:
    job_store, inbox, pool = queue_with([], {})

    assert not RunQueue(job_store, pool, inbox).execute().interrupted
