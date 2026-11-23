from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from queued_media_downloader.job_queue import RunQueue
from queued_media_downloader.jobs import (
    DownloadOptions,
    DownloadProgressed,
    FailureReason,
    FormatSelected,
    Job,
    JobCompleted,
    JobEvent,
    JobFailed,
    JobId,
    JobKind,
    JobStarted,
    JobStatus,
    MediaKey,
    SingleMediaFound,
)
from queued_media_downloader.workers import WorkerMessage
from tests.doubles.in_memory_job_store import InMemoryJobStore
from tests.doubles.scripted_worker_pool import ScriptedWorkerPool, ScriptKey

URL = "https://media.example/watch?v=a"
MEDIA_KEY = MediaKey(extractor_key="Example", media_id="a")
DOWNLOAD_OPTIONS = DownloadOptions(
    format_selector="bv*+ba/b",
    download_directory=Path("downloads"),
    output_template="%(title)s [%(id)s].%(ext)s",
    audio_only=False,
)
PROGRESS = DownloadProgressed(
    downloaded_bytes=10, total_bytes=100, bytes_per_second=5.0, eta_seconds=18
)


def single_media_script(url: str, media_id: str) -> dict[ScriptKey, list[JobEvent]]:
    """Guion de UC-03: la URL es un contenido y se descarga bien."""
    return {
        (JobKind.EXPANSION, url): [
            SingleMediaFound(
                media_key=MediaKey(extractor_key="Example", media_id=media_id),
                title=f"Title {media_id}",
            )
        ],
        (JobKind.DOWNLOAD, url): [
            FormatSelected(selected_format_id="18"),
            PROGRESS,
            JobCompleted(output_path=f"downloads/{media_id}.mp4"),
        ],
    }


def run_queue_with(
    urls: Sequence[str],
    script: Mapping[ScriptKey, Sequence[JobEvent]],
    worker_count: int = 1,
) -> tuple[InMemoryJobStore, ScriptedWorkerPool, RunQueue]:
    """Cola con las URLs ya encoladas, un pool con guion y su RunQueue."""
    job_store = InMemoryJobStore()
    for url in urls:
        job_store.create(Job.new_expansion(url, DOWNLOAD_OPTIONS))
    worker_pool = ScriptedWorkerPool(worker_count, script)
    return job_store, worker_pool, RunQueue(job_store, worker_pool)


def test_single_media_url_is_expanded_then_downloaded_to_completion() -> None:
    job_store, _, run_queue = run_queue_with([URL], single_media_script(URL, "a"))

    run_result = run_queue.execute()

    job = job_store.get(JobId(1))
    assert job.status is JobStatus.COMPLETED
    assert job.kind is JobKind.DOWNLOAD
    assert job.media_key == MEDIA_KEY
    assert job.title == "Title a"
    assert job.selected_format_id == "18"
    assert job.output_path == "downloads/a.mp4"
    assert run_result.failed_job_count == 0


def test_failed_job_is_recorded_and_the_rest_of_the_queue_continues() -> None:
    script: dict[ScriptKey, list[JobEvent]] = {
        (JobKind.EXPANSION, "https://broken"): [
            JobFailed(failure_reason=FailureReason.NETWORK, failure_message="Reset")
        ],
        **single_media_script(URL, "a"),
    }
    job_store, _, run_queue = run_queue_with(["https://broken", URL], script)

    run_result = run_queue.execute()

    failed_job = job_store.get(JobId(1))
    assert failed_job.status is JobStatus.FAILED
    assert failed_job.failure_reason is FailureReason.NETWORK
    assert failed_job.failure_message == "Reset"
    assert job_store.get(JobId(2)).status is JobStatus.COMPLETED
    assert run_result.failed_job_count == 1


def test_duplicate_media_is_skipped_and_not_downloaded_again() -> None:
    job_store, worker_pool, run_queue = run_queue_with(
        [URL, URL], single_media_script(URL, "a")
    )

    run_queue.execute()

    assert job_store.get(JobId(1)).status is JobStatus.COMPLETED
    duplicate = job_store.get(JobId(2))
    assert duplicate.status is JobStatus.SKIPPED
    assert duplicate.media_key == MEDIA_KEY
    downloads = [j for j in worker_pool.submitted_jobs if j.kind is JobKind.DOWNLOAD]
    assert [job.job_id for job in downloads] == [JobId(1)]


def test_jobs_are_submitted_as_running_only_to_idle_workers_oldest_first() -> None:
    urls = ["https://a", "https://b", "https://c"]
    script = {
        key: events
        for url, media_id in zip(urls, "abc", strict=True)
        for key, events in single_media_script(url, media_id).items()
    }
    job_store, worker_pool, run_queue = run_queue_with(urls, script, worker_count=2)

    run_queue.execute()

    submitted = worker_pool.submitted_jobs
    assert {job.status for job in submitted} == {JobStatus.RUNNING}
    # El job 1 vuelve a la cola como descarga y, por ser el más antiguo, se
    # envía antes que la expansión del job 3.
    assert [(job.job_id, job.kind) for job in submitted[:3]] == [
        (JobId(1), JobKind.EXPANSION),
        (JobId(2), JobKind.EXPANSION),
        (JobId(1), JobKind.DOWNLOAD),
    ]
    assert {job.status for job in job_store.all_jobs()} == {JobStatus.COMPLETED}


def test_every_worker_message_is_presented() -> None:
    presented: list[WorkerMessage] = []
    job_store = InMemoryJobStore()
    job_store.create(Job.new_expansion(URL, DOWNLOAD_OPTIONS))
    worker_pool = ScriptedWorkerPool(1, single_media_script(URL, "a"))

    RunQueue(job_store, worker_pool, present=presented.append).execute()

    presented_events = [message.job_event for message in presented]
    assert presented_events.count(JobStarted()) == 2
    assert PROGRESS in presented_events


def test_empty_queue_finishes_without_submitting_anything() -> None:
    _, worker_pool, run_queue = run_queue_with([], {})

    run_result = run_queue.execute()

    assert worker_pool.submitted_jobs == []
    assert run_result.failed_job_count == 0


def test_same_media_is_downloaded_once_as_video_and_once_as_audio() -> None:
    job_store = InMemoryJobStore()
    job_store.create(Job.new_expansion(URL, DOWNLOAD_OPTIONS))
    job_store.create(Job.new_expansion(URL, replace(DOWNLOAD_OPTIONS, audio_only=True)))
    worker_pool = ScriptedWorkerPool(1, single_media_script(URL, "a"))

    RunQueue(job_store, worker_pool).execute()

    assert {job.status for job in job_store.all_jobs()} == {JobStatus.COMPLETED}
    downloads = [j for j in worker_pool.submitted_jobs if j.kind is JobKind.DOWNLOAD]
    assert [job.download_options.audio_only for job in downloads] == [False, True]
