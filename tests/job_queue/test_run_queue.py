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
    PlaylistContext,
    PlaylistEntriesFound,
    PlaylistEntry,
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
PLAYLIST_URL = "https://media.example/playlist?list=PL1"
NESTED_PLAYLIST_URL = "https://media.example/playlist?list=PL2"
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


def video_url(media_id: str) -> str:
    return f"https://media.example/watch?v={media_id}"


def video_entry(
    playlist_index: int, media_id: str, *, is_available: bool = True
) -> PlaylistEntry:
    """Entrada de playlist que es un video del sitio de ejemplo."""
    return PlaylistEntry(
        url=video_url(media_id),
        playlist_index=playlist_index,
        kind=JobKind.DOWNLOAD,
        title=f"Title {media_id}",
        media_key=MediaKey(extractor_key="Example", media_id=media_id),
        is_available=is_available,
    )


def playlist_batch(
    playlist_id: str, *playlist_entries: PlaylistEntry
) -> PlaylistEntriesFound:
    return PlaylistEntriesFound(
        playlist_id=playlist_id,
        playlist_title=f"Playlist {playlist_id}",
        playlist_entries=playlist_entries,
    )


def download_script(*media_ids: str) -> dict[ScriptKey, list[JobEvent]]:
    """Guion de descarga correcta para los videos indicados."""
    return {
        (JobKind.DOWNLOAD, video_url(media_id)): [
            FormatSelected(selected_format_id="18"),
            JobCompleted(output_path=f"downloads/{media_id}.mp4"),
        ]
        for media_id in media_ids
    }


def downloaded_urls(worker_pool: ScriptedWorkerPool) -> list[str]:
    return [
        job.url for job in worker_pool.submitted_jobs if job.kind is JobKind.DOWNLOAD
    ]


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

    RunQueue(
        job_store,
        worker_pool,
        present=lambda message, _job: presented.append(message),
    ).execute()

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
    script = single_media_script(URL, "a")
    # El guion no distingue video de audio, y en realidad sus rutas difieren
    # (subcarpeta audio, T23); la ruta no es lo que prueba este caso.
    script[(JobKind.DOWNLOAD, URL)][-1] = JobCompleted(output_path=None)
    worker_pool = ScriptedWorkerPool(1, script)

    RunQueue(job_store, worker_pool).execute()

    assert {job.status for job in job_store.all_jobs()} == {JobStatus.COMPLETED}
    downloads = [j for j in worker_pool.submitted_jobs if j.kind is JobKind.DOWNLOAD]
    assert [job.download_options.audio_only for job in downloads] == [False, True]


def test_presentation_receives_the_job_as_the_event_left_it() -> None:
    presented: list[tuple[JobEvent, Job | None]] = []
    job_store = InMemoryJobStore()
    job_store.create(Job.new_expansion(URL, DOWNLOAD_OPTIONS))
    job_store.create(Job.new_expansion(URL, DOWNLOAD_OPTIONS))
    worker_pool = ScriptedWorkerPool(1, single_media_script(URL, "a"))

    RunQueue(
        job_store,
        worker_pool,
        present=lambda message, job: presented.append((message.job_event, job)),
    ).execute()

    found_statuses = [
        job.status
        for job_event, job in presented
        if isinstance(job_event, SingleMediaFound) and job is not None
    ]
    assert found_statuses == [JobStatus.PENDING, JobStatus.SKIPPED]
    assert all(job is None for job_event, job in presented if job_event == PROGRESS)


def test_playlist_batches_become_children_that_are_downloaded() -> None:
    script: dict[ScriptKey, list[JobEvent]] = {
        (JobKind.EXPANSION, PLAYLIST_URL): [
            playlist_batch("PL1", video_entry(1, "a"), video_entry(2, "b")),
            playlist_batch("PL1", video_entry(3, "c")),
            JobCompleted(output_path=None),
        ],
        **download_script("a", "b", "c"),
    }
    job_store, worker_pool, run_queue = run_queue_with([PLAYLIST_URL], script)

    run_result = run_queue.execute()

    playlist_job, *children = job_store.all_jobs()
    assert playlist_job.status is JobStatus.COMPLETED
    assert playlist_job.kind is JobKind.EXPANSION
    assert [child.url for child in children] == [video_url(m) for m in "abc"]
    assert {child.parent_id for child in children} == {playlist_job.job_id}
    assert children[2].playlist_context == PlaylistContext(
        playlist_id="PL1",
        playlist_title="Playlist PL1",
        playlist_index=3,
        playlist_entry_count=None,
    )
    assert {child.status for child in children} == {JobStatus.COMPLETED}
    assert downloaded_urls(worker_pool) == [video_url(m) for m in "abc"]
    assert run_result.failed_job_count == 0


def test_duplicate_and_unavailable_entries_are_skipped_children() -> None:
    script: dict[ScriptKey, list[JobEvent]] = {
        **single_media_script(video_url("a"), "a"),
        (JobKind.EXPANSION, PLAYLIST_URL): [
            playlist_batch(
                "PL1",
                video_entry(1, "a"),  # A2: ya descargado por el job 1
                video_entry(2, "b"),
                video_entry(3, "b"),  # A2: repetido en el mismo lote
                video_entry(4, "p", is_available=False),  # A3: privado
            ),
            playlist_batch("PL1", video_entry(5, "b")),  # A2: de un lote anterior
            JobCompleted(output_path=None),
        ],
        **download_script("b"),
    }
    job_store, worker_pool, run_queue = run_queue_with(
        [video_url("a"), PLAYLIST_URL], script
    )

    run_result = run_queue.execute()

    children = [job for job in job_store.all_jobs() if job.parent_id is not None]
    assert [child.status for child in children] == [
        JobStatus.SKIPPED,
        JobStatus.COMPLETED,
        JobStatus.SKIPPED,
        JobStatus.SKIPPED,
        JobStatus.SKIPPED,
    ]
    assert downloaded_urls(worker_pool) == [video_url("a"), video_url("b")]
    assert run_result.failed_job_count == 0


def test_nested_playlist_entry_is_expanded_in_turn() -> None:
    nested_entry = PlaylistEntry(
        url=NESTED_PLAYLIST_URL,
        playlist_index=2,
        kind=JobKind.EXPANSION,
        title="Tab",
        media_key=None,
        is_available=True,
    )
    script: dict[ScriptKey, list[JobEvent]] = {
        (JobKind.EXPANSION, PLAYLIST_URL): [
            playlist_batch("PL1", video_entry(1, "a"), nested_entry),
            JobCompleted(output_path=None),
        ],
        (JobKind.EXPANSION, NESTED_PLAYLIST_URL): [
            playlist_batch("PL2", video_entry(1, "d")),
            JobCompleted(output_path=None),
        ],
        **download_script("a", "d"),
    }
    job_store, worker_pool, run_queue = run_queue_with([PLAYLIST_URL], script)

    run_queue.execute()

    nested_job = job_store.get(JobId(3))
    assert nested_job.kind is JobKind.EXPANSION
    assert nested_job.status is JobStatus.COMPLETED
    assert nested_job.parent_id == JobId(1)
    grandchild = job_store.get(JobId(4))
    assert grandchild.parent_id == JobId(3)
    assert grandchild.playlist_context is not None
    assert grandchild.playlist_context.playlist_id == "PL2"
    assert sorted(downloaded_urls(worker_pool)) == [video_url("a"), video_url("d")]
    assert {job.status for job in job_store.all_jobs()} == {JobStatus.COMPLETED}


def test_job_whose_output_file_belongs_to_another_job_fails() -> None:
    # Dos contenidos distintos con el mismo nombre final: yt-dlp toma el
    # segundo por ya descargado y devuelve la ruta del primero (R-14).
    shared_output = "downloads/video.mp4"
    script: dict[ScriptKey, list[JobEvent]] = {
        **{
            key: events
            for media_id in ("a", "b")
            for key, events in single_media_script(
                video_url(media_id), media_id
            ).items()
            if key[0] is JobKind.EXPANSION
        },
        (JobKind.DOWNLOAD, video_url("a")): [JobCompleted(output_path=shared_output)],
        (JobKind.DOWNLOAD, video_url("b")): [JobCompleted(output_path=shared_output)],
    }
    job_store, _, run_queue = run_queue_with([video_url("a"), video_url("b")], script)

    run_result = run_queue.execute()

    first, second = job_store.all_jobs()
    assert first.status is JobStatus.COMPLETED
    assert first.output_path == shared_output
    assert second.status is JobStatus.FAILED
    assert second.failure_reason is FailureReason.FILESYSTEM
    assert second.output_path is None
    assert "already belongs to another job" in (second.failure_message or "")
    assert run_result.failed_job_count == 1
