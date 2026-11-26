"""Crea las implementaciones de los contratos para la línea de comandos.

Es el único módulo que importa el interior de otros componentes (diseño,
Parte 1, §3, regla 3).
"""

import functools
import sqlite3
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from queued_media_downloader.configuration import Settings, project_root
from queued_media_downloader.diagnostics import DiagnoseEnvironment
from queued_media_downloader.ffmpeg_discovery import FfmpegLocator
from queued_media_downloader.ffmpeg_discovery.file_system_ffmpeg_locator import (
    VENDORED_BUILD_NAME,
    FileSystemFfmpegLocator,
)
from queued_media_downloader.job_storage import (
    JobRequestInbox,
    JobStore,
    JobStoreLockedError,
    JobStoreUnavailableError,
)
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_request_inbox import (
    SqliteJobRequestInbox,
)
from queued_media_downloader.job_storage.sqlite_job_store import (
    LOCKED_DATABASE_MESSAGE,
    SqliteJobStore,
)
from queued_media_downloader.media_extraction import MediaSourceSettings
from queued_media_downloader.media_extraction.yt_dlp_javascript_runtime import (
    find_deno,
)
from queued_media_downloader.media_extraction.yt_dlp_media_source import (
    YtDlpMediaSource,
)
from queued_media_downloader.workers import WorkerPool
from queued_media_downloader.workers.posix_process_tree_terminator import (
    PosixProcessTreeTerminator,
)
from queued_media_downloader.workers.process_tree_terminator import (
    ProcessTreeTerminator,
)
from queued_media_downloader.workers.process_worker_pool import ProcessWorkerPool

if sys.platform == "win32":
    from queued_media_downloader.workers.windows_process_tree_terminator import (
        WindowsProcessTreeTerminator,
    )

DATABASE_FILE_NAME = "queue.sqlite3"
YT_DLP_CACHE_DIRECTORY_NAME = "yt-dlp-cache"
# Reclamaciones de los nombres finales (R-14): una carpeta por cola.
OUTPUT_CLAIMS_DIRECTORY_NAME = "output-claims"
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
    with _translating_locked_database():
        connection = _open_queue_database(state_directory)
        try:
            yield SqliteJobStore(connection)
        finally:
            connection.close()


@contextmanager
def open_job_store_and_inbox(
    state_directory: Path,
) -> Iterator[tuple[JobStore, JobRequestInbox]]:
    """Abre el job store y la bandeja de job requests sobre una sola conexión."""
    state_directory.mkdir(parents=True, exist_ok=True)
    with _translating_locked_database():
        connection = _open_queue_database(state_directory)
        try:
            yield SqliteJobStore(connection), SqliteJobRequestInbox(connection)
        finally:
            connection.close()


def _open_queue_database(state_directory: Path) -> sqlite3.Connection:
    """Abre y migra la base de datos de la cola.

    Raises:
        JobStoreLockedError: Si otro proceso la tiene ocupada.
        JobStoreUnavailableError: Si no se puede abrir o una migración falla
            (open_database ya deshizo la migración y cerró la conexión).
    """
    database_path = state_directory / DATABASE_FILE_NAME
    try:
        return open_database(database_path)
    except sqlite3.DatabaseError as database_error:
        if LOCKED_DATABASE_MESSAGE in str(database_error):
            raise
        message = f"cannot open the queue database {database_path}: {database_error}"
        raise JobStoreUnavailableError(message) from database_error


@contextmanager
def _translating_locked_database() -> Iterator[None]:
    """Convierte "database is locked" de SQLite en JobStoreLockedError.

    Otro proceso puede tener la base de datos ocupada más allá de
    busy_timeout al abrirla, al migrarla o en cualquier escritura de un
    comando; cada comando lo informa sin traza (UC-02 A3, UC-05 E2…).
    """
    try:
        yield
    except sqlite3.OperationalError as operational_error:
        if LOCKED_DATABASE_MESSAGE not in str(operational_error):
            raise
        raise JobStoreLockedError(str(operational_error)) from operational_error


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
        output_claims_directory=output_claims_directory(settings),
        ffmpeg_location=ffmpeg_location,
        max_filename_length=settings.max_filename_length,
        progress_interval_seconds=settings.progress_interval_seconds,
    )
    worker_pool = ProcessWorkerPool(
        settings.worker_count,
        functools.partial(YtDlpMediaSource, media_source_settings),
        create_process_tree_terminator,
        max_jobs_per_worker=settings.max_jobs_per_worker,
    )
    try:
        yield worker_pool
    finally:
        try:
            worker_pool.shut_down()
        except KeyboardInterrupt:
            # Segundo Ctrl+C mientras los workers terminaban por su cuenta: se
            # termina su árbol sin esperar, nunca se deja un worker vivo.
            worker_pool.shut_down(immediately=True)
            raise


def output_claims_directory(settings: Settings) -> Path:
    """Carpeta de las reclamaciones de nombres finales de esta cola (R-14)."""
    return settings.state_directory / OUTPUT_CLAIMS_DIRECTORY_NAME


def create_process_tree_terminator() -> ProcessTreeTerminator:
    """Terminador del árbol de un worker para la plataforma actual (ADR-0029).

    Windows: un Job Object por worker. POSIX: un grupo de procesos, para
    ejecutar el proyecto y sus pruebas en cualquier sistema.
    """
    if sys.platform == "win32":
        return WindowsProcessTreeTerminator()
    return PosixProcessTreeTerminator()


def create_diagnose_environment(settings: Settings) -> DiagnoseEnvironment:
    """Diagnóstico con el ffmpeg, el deno y la base de datos que usará run."""
    return DiagnoseEnvironment(
        ffmpeg_locator=create_ffmpeg_locator(settings),
        find_javascript_runtime=find_deno,
        open_database=functools.partial(
            read_database_schema_version, settings.state_directory
        ),
    )


def read_database_schema_version(state_directory: Path) -> int:
    """Abre la base de datos, la migra si hace falta y devuelve su versión."""
    state_directory.mkdir(parents=True, exist_ok=True)
    connection = open_database(state_directory / DATABASE_FILE_NAME)
    try:
        schema_version: int = connection.execute("PRAGMA user_version").fetchone()[0]
    finally:
        connection.close()
    return schema_version
