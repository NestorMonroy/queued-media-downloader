"""Crea las implementaciones de los contratos para la línea de comandos.

Es el único módulo que importa el interior de otros componentes (diseño,
Parte 1, §3, regla 3).
"""

import functools
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from queued_media_downloader.configuration import Settings, project_root
from queued_media_downloader.ffmpeg_discovery import FfmpegLocator
from queued_media_downloader.ffmpeg_discovery.file_system_ffmpeg_locator import (
    VENDORED_BUILD_NAME,
    FileSystemFfmpegLocator,
)
from queued_media_downloader.job_storage import JobStore
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_store import SqliteJobStore
from queued_media_downloader.media_extraction import MediaSourceSettings
from queued_media_downloader.media_extraction.yt_dlp_media_source import (
    YtDlpMediaSource,
)
from queued_media_downloader.workers import WorkerPool
from queued_media_downloader.workers.process_worker_pool import ProcessWorkerPool

DATABASE_FILE_NAME = "queue.sqlite3"
YT_DLP_CACHE_DIRECTORY_NAME = "yt-dlp-cache"
FFMPEG_VERIFICATION_FILE_NAME = "ffmpeg-verification.json"


def create_ffmpeg_locator(settings: Settings) -> FfmpegLocator:
    """Localizador de ffmpeg con la build de vendor/ y la caché en state/."""
    return FileSystemFfmpegLocator(
        configured_path=settings.ffmpeg_path,
        vendored_build_directory=project_root()
        / "vendor"
        / "ffmpeg"
        / VENDORED_BUILD_NAME,
        verification_cache_file=settings.state_directory
        / FFMPEG_VERIFICATION_FILE_NAME,
    )


@contextmanager
def open_job_store(state_directory: Path) -> Iterator[JobStore]:
    """Abre el job store de state_directory y cierra su conexión al terminar."""
    state_directory.mkdir(parents=True, exist_ok=True)
    connection = open_database(state_directory / DATABASE_FILE_NAME)
    try:
        yield SqliteJobStore(connection)
    finally:
        connection.close()


@contextmanager
def open_worker_pool(
    settings: Settings, ffmpeg_location: Path | None
) -> Iterator[WorkerPool]:
    """Arranca el pool de procesos con yt-dlp y lo apaga al terminar.

    ffmpeg_location es el de la instalación ya verificada; None deja que
    yt-dlp busque ffmpeg en el PATH. La fábrica de MediaSource es un
    functools.partial de una clase, que pickle puede enviar a cada worker.
    """
    media_source_settings = MediaSourceSettings(
        cache_directory=settings.state_directory / YT_DLP_CACHE_DIRECTORY_NAME,
        ffmpeg_location=ffmpeg_location,
        max_filename_length=settings.max_filename_length,
        progress_interval_seconds=settings.progress_interval_seconds,
    )
    worker_pool = ProcessWorkerPool(
        settings.worker_count,
        functools.partial(YtDlpMediaSource, media_source_settings),
    )
    try:
        yield worker_pool
    finally:
        worker_pool.shut_down()
