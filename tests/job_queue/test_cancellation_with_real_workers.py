"""Cancelar con workers reales (UC-05, T38): cooperativa y forzada."""

import functools
import multiprocessing
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from queued_media_downloader.job_queue import EnqueueMedia, RunQueue
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_request_inbox import (
    SqliteJobRequestInbox,
)
from queued_media_downloader.job_storage.sqlite_job_store import SqliteJobStore
from queued_media_downloader.jobs import (
    DownloadOptions,
    DownloadProgressed,
    Job,
    JobId,
    JobKind,
    JobRequest,
    JobRequestType,
    JobStarted,
    JobStatus,
    MediaKey,
    SingleMediaFound,
)
from queued_media_downloader.media_extraction import MediaSource, MediaSourceSettings
from queued_media_downloader.media_extraction.yt_dlp_media_source import (
    YtDlpMediaSource,
)
from queued_media_downloader.workers import WorkerMessage
from queued_media_downloader.workers.process_worker_pool import ProcessWorkerPool
from tests.conftest import SLOW_MEDIA_NAME
from tests.doubles.fake_media_source import (
    FakeMediaSource,
    ScriptedBehavior,
    ScriptKey,
    SpawnChild,
)
from tests.doubles.process_tree import (
    WatchedProcess,
    platform_process_tree_terminator,
    wait_for_roles,
)

DOWNLOAD_OPTIONS = DownloadOptions(
    format_selector="bv*+ba/b",
    download_directory=Path("downloads"),
    output_template="%(title)s [%(id)s].%(ext)s",
    audio_only=False,
)


@contextmanager
def opened_queue(
    database_path: Path,
) -> Iterator[tuple[SqliteJobStore, SqliteJobRequestInbox]]:
    connection = open_database(database_path)
    try:
        yield SqliteJobStore(connection), SqliteJobRequestInbox(connection)
    finally:
        connection.close()


class CancelWhen:
    """Presentación que pide cancelar el job al ver cierto job event.

    skip ignora las primeras apariciones: la descarga es la segunda ejecución
    del job 1, tras su expansión.
    """

    def __init__(
        self,
        inbox: SqliteJobRequestInbox,
        event_type: type[object],
        skip: int,
        before_cancelling: Callable[[], None] | None = None,
    ) -> None:
        self._inbox = inbox
        self._event_type = event_type
        self._remaining_skips = skip
        self._before_cancelling = before_cancelling
        self.requested_at: float | None = None

    def __call__(self, message: WorkerMessage, job: Job | None) -> None:
        del job
        if self.requested_at is not None:
            return
        if not isinstance(message.job_event, self._event_type):
            return
        if self._remaining_skips > 0:
            self._remaining_skips -= 1
            return
        if self._before_cancelling is not None:
            self._before_cancelling()
        cancel = JobRequest(job_id=message.job_id, request_type=JobRequestType.CANCEL)
        self._inbox.create_many([cancel])
        self.requested_at = time.monotonic()


def run_cancelling(
    tmp_path: Path,
    media_source_factory: Callable[[], MediaSource],
    url: str,
    download_options: DownloadOptions,
    cancel_on: type[object],
    cancellation_grace_seconds: float,
    skip: int = 0,
    before_cancelling: Callable[[], None] | None = None,
) -> tuple[Job, float]:
    """Encola url, ejecuta la cola y cancela la descarga al ver cancel_on."""
    with opened_queue(tmp_path / "queue.sqlite3") as (job_store, inbox):
        EnqueueMedia(job_store).execute([url], download_options)
        pool = ProcessWorkerPool(
            1, media_source_factory, platform_process_tree_terminator
        )
        cancel_download = CancelWhen(inbox, cancel_on, skip, before_cancelling)
        try:
            RunQueue(
                job_store,
                pool,
                inbox,
                present=cancel_download,
                cancellation_grace_seconds=cancellation_grace_seconds,
            ).execute()
            finished_at = time.monotonic()
        finally:
            pool.shut_down()
        assert cancel_download.requested_at is not None
        return job_store.get(JobId(1)), finished_at - cancel_download.requested_at


def test_real_download_stops_at_its_next_progress_and_keeps_its_partial_file(
    local_media_server: str, tmp_path: Path
) -> None:
    settings = MediaSourceSettings(
        cache_directory=tmp_path / "cache",
        output_claims_directory=tmp_path / "output-claims",
        ffmpeg_location=None,
        max_filename_length=150,
        progress_interval_seconds=0.2,
    )
    download_options = replace(DOWNLOAD_OPTIONS, download_directory=tmp_path / "dl")

    job, seconds_to_stop = run_cancelling(
        tmp_path,
        functools.partial(YtDlpMediaSource, settings),
        f"{local_media_server}/{SLOW_MEDIA_NAME}",
        download_options,
        cancel_on=DownloadProgressed,
        cancellation_grace_seconds=60.0,
    )

    assert job.status is JobStatus.CANCELLED
    # Cooperativa: mucho antes del plazo de 60 s y del final de la descarga.
    assert seconds_to_stop < 5.0
    # UC-05, postcondición: el parcial se conserva para un posible reintento.
    partial_files = list(job.partial_directory().glob("*.part"))
    assert partial_files and partial_files[0].stat().st_size > 0
    assert multiprocessing.active_children() == []


def test_job_without_progress_is_terminated_with_its_child_after_the_grace_period(
    tmp_path: Path,
) -> None:
    # A2: como ffmpeg uniendo archivos, el job no publica nada y no ve la bandera.
    url = "https://media.example/watch?v=a"
    pid_file = tmp_path / "child.pids"
    script: dict[ScriptKey, ScriptedBehavior] = {
        ("expand", url): [
            SingleMediaFound(
                media_key=MediaKey(extractor_key="Example", media_id="a"), title="A"
            )
        ],
        ("download", url): SpawnChild(str(pid_file), then_crash=False),
    }
    watched_children: list[WatchedProcess] = []

    def watch_child_before_cancelling() -> None:
        # El handle se abre con el hijo vivo: tras terminarlo, su PID ya no
        # existe y Windows no deja abrirlo (T42-D1, WinError 87).
        child_id = wait_for_roles(pid_file, ("child",))["child"]
        watched_children.append(WatchedProcess(child_id))

    job, seconds_to_stop = run_cancelling(
        tmp_path,
        functools.partial(FakeMediaSource, script),
        url,
        DOWNLOAD_OPTIONS,
        cancel_on=JobStarted,
        cancellation_grace_seconds=1.0,
        skip=1,
        before_cancelling=watch_child_before_cancelling,
    )
    [child] = watched_children

    try:
        assert job.kind is JobKind.DOWNLOAD
        assert job.status is JobStatus.CANCELLED
        assert seconds_to_stop >= 1.0
        assert not child.is_alive()
        assert multiprocessing.active_children() == []
    finally:
        child.kill()
        child.close()
