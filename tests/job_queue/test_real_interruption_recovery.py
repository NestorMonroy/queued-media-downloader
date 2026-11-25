"""Criterio obligatorio entre los slices B y C (plan de E2, §5.1).

Una descarga real, contra un servidor que envía despacio, se interrumpe a
medias terminando el árbol de su worker con el mecanismo de D1. Después se
"reinicia": otra conexión a la base de datos, otro pool, la recuperación de
T31 y la cola de UC-03. La descarga debe continuar desde su .part pidiendo solo
los bytes que faltan.

Se ejecuta en cualquier sistema con el terminador de la plataforma; en la
campaña final se ejecuta también en Windows (paso 8). Lo que esta prueba no
cubre, y cubre el paso manual de la campaña, es la muerte del proceso principal.
"""

import functools
import multiprocessing
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from queued_media_downloader.job_queue import (
    EnqueueMedia,
    RecoverInterruptedJobs,
    RunQueue,
)
from queued_media_downloader.job_queue.job_event_applier import JobEventApplier
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_request_inbox import (
    SqliteJobRequestInbox,
)
from queued_media_downloader.job_storage.sqlite_job_store import SqliteJobStore
from queued_media_downloader.jobs import (
    DownloadOptions,
    Job,
    JobKind,
    JobStatus,
)
from queued_media_downloader.media_extraction import MediaSourceSettings
from queued_media_downloader.media_extraction.yt_dlp_media_source import (
    YtDlpMediaSource,
)
from queued_media_downloader.workers.process_worker_pool import ProcessWorkerPool
from tests.conftest import SLOW_MEDIA_CONTENT, SLOW_MEDIA_NAME
from tests.doubles.process_tree import platform_process_tree_terminator

# Bytes del .part a partir de los cuales se interrumpe: una cantidad conocida,
# lejos del principio y del final del contenido.
INTERRUPT_AFTER_BYTES = 128 * 1024
WAIT_TIMEOUT_SECONDS = 60.0


@contextmanager
def opened_queue(
    database_path: Path,
) -> Iterator[tuple[SqliteJobStore, SqliteJobRequestInbox]]:
    connection = open_database(database_path)
    try:
        yield SqliteJobStore(connection), SqliteJobRequestInbox(connection)
    finally:
        connection.close()


def start_pool(tmp_path: Path) -> ProcessWorkerPool:
    settings = MediaSourceSettings(
        cache_directory=tmp_path / "cache",
        ffmpeg_location=None,
        max_filename_length=150,
        progress_interval_seconds=0.5,
    )
    return ProcessWorkerPool(
        1,
        functools.partial(YtDlpMediaSource, settings),
        platform_process_tree_terminator,
    )


def run_until_partially_downloaded(
    job_store: SqliteJobStore, worker_pool: ProcessWorkerPool
) -> Job:
    """Ejecuta la cola hasta que el .part de la descarga pase del umbral.

    Hace lo mismo que RunQueue, pero se detiene en mitad de la descarga.
    """
    applier = JobEventApplier(job_store)
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        for pending_job in job_store.get_next_pending(worker_pool.count_idle_workers()):
            running_job = pending_job.start()
            job_store.update(running_job)
            worker_pool.submit(running_job)
        for message in worker_pool.collect_events(timeout_seconds=0.05):
            applier.apply(message)
        download = _running_download(job_store)
        if download is not None and _partial_size(download) >= INTERRUPT_AFTER_BYTES:
            return download
    timeout_message = "The download did not reach the interruption point"
    raise TimeoutError(timeout_message)


def _running_download(job_store: SqliteJobStore) -> Job | None:
    running = job_store.get_with_status({JobStatus.RUNNING})
    downloads = [job for job in running if job.kind is JobKind.DOWNLOAD]
    return downloads[0] if downloads else None


def _partial_size(job: Job) -> int:
    partial_files = list(job.partial_directory().glob("*.part"))
    return partial_files[0].stat().st_size if partial_files else 0


def test_download_interrupted_for_real_resumes_from_its_partial_file(
    local_media_server: str,
    tmp_path: Path,
    media_requests: list[tuple[str, str | None]],
) -> None:
    database_path = tmp_path / "queue.sqlite3"
    downloads = tmp_path / "downloads"
    media_url = f"{local_media_server}/{SLOW_MEDIA_NAME}"
    download_options = DownloadOptions(
        format_selector="bv*+ba/b",
        download_directory=downloads,
        output_template="%(title)s [%(id)s].%(ext)s",
        audio_only=False,
    )

    # 1-3. Descarga real, interrumpida a medias; se termina el árbol del worker.
    with opened_queue(database_path) as (job_store, _):
        EnqueueMedia(job_store).execute([media_url], download_options)
        worker_pool = start_pool(tmp_path)
        try:
            interrupted = run_until_partially_downloaded(job_store, worker_pool)
            assert interrupted.job_id is not None
            job_id = interrupted.job_id
            assert worker_pool.terminate_worker_running(job_id)
        finally:
            worker_pool.shut_down()
    assert multiprocessing.active_children() == []

    # 4. Estado y archivos preservados; nada sigue escribiendo el .part.
    with opened_queue(database_path) as (job_store, _):
        interrupted = job_store.get(job_id)
    partial_size = _partial_size(interrupted)
    time.sleep(0.5)
    assert _partial_size(interrupted) == partial_size
    assert INTERRUPT_AFTER_BYTES <= partial_size < len(SLOW_MEDIA_CONTENT)
    assert interrupted.status is JobStatus.RUNNING
    assert interrupted.selected_format_id == "mp4"

    # 5-6. "Reinicio": otra conexión, otro pool, recuperación y cola.
    media_requests.clear()
    with opened_queue(database_path) as (job_store, inbox):
        recovery = RecoverInterruptedJobs(job_store).execute()
        worker_pool = start_pool(tmp_path)
        try:
            run_result = RunQueue(job_store, worker_pool, inbox).execute()
        finally:
            worker_pool.shut_down()
        finished = job_store.get(job_id)

    output_path = downloads / "slow [slow].mp4"
    assert recovery.requeued_job_count == 1
    # 7. Solo los bytes que faltan (más la extracción, que no descarga).
    assert media_requests == [
        (f"/{SLOW_MEDIA_NAME}", None),
        (f"/{SLOW_MEDIA_NAME}", f"bytes={partial_size}-"),
    ]
    # 8. Archivo íntegro.
    assert output_path.read_bytes() == SLOW_MEDIA_CONTENT
    # 9. Estado definitivo.
    assert run_result.failed_job_count == 0
    assert finished.status is JobStatus.COMPLETED
    assert finished.output_path == str(output_path)
    # 10. Sin procesos ni parciales del job.
    assert multiprocessing.active_children() == []
    assert not interrupted.partial_directory().exists()
