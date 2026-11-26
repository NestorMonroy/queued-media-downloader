"""RunQueue procesa las job requests de cancel (UC-05, T37)."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from queued_media_downloader.job_queue import RunQueue
from queued_media_downloader.jobs import (
    DownloadOptions,
    FormatSelected,
    Job,
    JobCompleted,
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


def retry(job_id: int) -> JobRequest:
    return JobRequest(job_id=JobId(job_id), request_type=JobRequestType.RETRY)


def test_retried_failed_job_runs_again_as_a_new_attempt() -> None:
    # UC-07: FAILED vuelve a PENDING, incrementa attempt_count y se ejecuta.
    script: dict[ScriptKey, list[ScriptStep]] = {
        (JobKind.EXPANSION, URL): [FOUND_A],
        (JobKind.DOWNLOAD, URL): [JobCompleted(output_path="downloads/a.mp4")],
    }
    job_store, inbox, pool = queue_with([URL], script)
    job_store.update(replace(job_store.get(JobId(1)), status=JobStatus.FAILED))
    inbox.create_many([retry(1)])

    RunQueue(job_store, pool, inbox).execute()

    retried = job_store.get(JobId(1))
    assert retried.status is JobStatus.COMPLETED
    assert retried.attempt_count == 1
    assert retried.failure_reason is None
    assert inbox.get_unprocessed() == []


def test_retry_request_for_a_completed_job_changes_nothing() -> None:
    job_store, inbox, pool = queue_with([URL], {})
    job_store.update(replace(job_store.get(JobId(1)), status=JobStatus.COMPLETED))
    inbox.create_many([retry(1)])

    RunQueue(job_store, pool, inbox).execute()

    assert job_store.get(JobId(1)).status is JobStatus.COMPLETED
    assert job_store.get(JobId(1)).attempt_count == 0


def test_retrying_a_playlist_brings_back_its_cancelled_children() -> None:
    # UC-04 A6 y la simetría con cancelar una playlist (UC-05 A4).
    child_url = "https://media.example/watch?v=b"
    script: dict[ScriptKey, list[ScriptStep]] = {
        (JobKind.EXPANSION, PLAYLIST_URL): [JobCompleted(output_path=None)],
        (JobKind.DOWNLOAD, child_url): [JobCompleted(output_path="downloads/b.mp4")],
    }
    job_store, inbox, pool = queue_with([PLAYLIST_URL], script)
    job_store.update(replace(job_store.get(JobId(1)), status=JobStatus.CANCELLED))
    child = replace(
        Job.new_expansion(child_url, DOWNLOAD_OPTIONS),
        kind=JobKind.DOWNLOAD,
        parent_id=JobId(1),
    )
    child_id = job_store.create(child)
    job_store.update(replace(job_store.get(child_id), status=JobStatus.CANCELLED))
    inbox.create_many([retry(1)])

    RunQueue(job_store, pool, inbox).execute()

    assert job_store.get(JobId(1)).status is JobStatus.COMPLETED
    assert job_store.get(child_id).status is JobStatus.COMPLETED
    assert job_store.get(child_id).attempt_count == 1


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


def test_keep_waiting_runs_jobs_enqueued_after_the_queue_emptied() -> None:
    # UC-03 A5: run no termina al vaciarse la cola; otra terminal encola después.
    script: dict[ScriptKey, list[ScriptStep]] = {
        (JobKind.EXPANSION, URL): [FOUND_A],
        (JobKind.DOWNLOAD, URL): [JobCompleted(output_path="downloads/a.mp4")],
    }
    job_store, inbox, pool = queue_with([], script)
    checks = 0

    def enqueue_later_then_stop() -> bool:
        nonlocal checks
        checks += 1
        if checks == 5:
            job_store.create(Job.new_expansion(URL, DOWNLOAD_OPTIONS))
        jobs = job_store.all_jobs()
        return bool(jobs) and jobs[0].status is JobStatus.COMPLETED

    run_result = RunQueue(
        job_store,
        pool,
        inbox,
        keep_waiting=True,
        stop_requested=enqueue_later_then_stop,
    ).execute()

    assert checks > 5
    assert job_store.get(JobId(1)).status is JobStatus.COMPLETED
    assert run_result.interrupted


def test_retrying_a_playlist_is_idempotent_and_never_downloads_twice() -> None:
    # Decisión del Responsable: retry de una playlist incluye sus entradas
    # FAILED y CANCELLED, nunca las COMPLETED; peticiones repetidas no suman
    # intentos ni descargas.
    child_urls = {
        media_id: f"https://media.example/watch?v={media_id}" for media_id in "abc"
    }
    entries = [
        PlaylistEntry(
            url=child_urls[media_id],
            playlist_index=index,
            kind=JobKind.DOWNLOAD,
            title=media_id.upper(),
            media_key=MediaKey(extractor_key="Example", media_id=media_id),
            is_available=True,
        )
        for index, media_id in enumerate("abc", start=1)
    ]
    script: dict[ScriptKey, list[ScriptStep]] = {
        (JobKind.EXPANSION, PLAYLIST_URL): [
            PlaylistEntriesFound(
                playlist_id="PL1",
                playlist_title="Playlist",
                playlist_entries=tuple(entries),
            ),
            JobCompleted(output_path=None),
        ],
        **{
            (JobKind.DOWNLOAD, child_urls[media_id]): [
                JobCompleted(output_path=f"downloads/{media_id}.mp4")
            ]
            for media_id in "bc"
        },
    }
    job_store, inbox, pool = queue_with([PLAYLIST_URL], script)
    job_store.update(replace(job_store.get(JobId(1)), status=JobStatus.FAILED))
    child_ids = {}
    for entry, status in zip(
        entries,
        (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED),
        strict=True,
    ):
        child_id = job_store.create(
            replace(
                Job.new_expansion(entry.url, DOWNLOAD_OPTIONS),
                kind=JobKind.DOWNLOAD,
                parent_id=JobId(1),
                media_key=entry.media_key,
            )
        )
        output_path = "downloads/a.mp4" if status is JobStatus.COMPLETED else None
        job_store.update(
            replace(job_store.get(child_id), status=status, output_path=output_path)
        )
        child_ids[entry.title] = child_id
    inbox.create_many([retry(1), retry(1), retry(int(child_ids["B"]))])

    RunQueue(job_store, pool, inbox).execute()

    downloads = [job.url for job in pool.submitted_jobs if job.kind is JobKind.DOWNLOAD]
    assert sorted(downloads) == [child_urls["b"], child_urls["c"]]
    attempts = {title: job_store.get(i).attempt_count for title, i in child_ids.items()}
    assert attempts == {"A": 0, "B": 1, "C": 1}
    assert job_store.get(JobId(1)).attempt_count == 1
    assert {job_store.get(i).status for i in child_ids.values()} == {
        JobStatus.COMPLETED
    }
    assert job_store.get(child_ids["A"]).output_path == "downloads/a.mp4"
    # La nueva expansión encuentra las tres entradas: todas son duplicadas.
    new_children = [
        job
        for job in job_store.all_jobs()
        if job.job_id not in {JobId(1), *child_ids.values()}
    ]
    assert {job.status for job in new_children} == {JobStatus.SKIPPED}
    assert inbox.get_unprocessed() == []
