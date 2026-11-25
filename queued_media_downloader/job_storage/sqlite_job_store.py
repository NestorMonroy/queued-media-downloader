"""Implementación de JobStore sobre SQLite."""

import json
import sqlite3
from collections.abc import Collection, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from queued_media_downloader.job_storage.job_store import (
    DuplicateActiveDownloadError,
    DuplicateOutputPathError,
    JobNotFoundError,
    JobStoreLockedError,
)
from queued_media_downloader.jobs import (
    DownloadOptions,
    FailureReason,
    Job,
    JobId,
    JobKind,
    JobStatus,
    MediaKey,
    PlaylistContext,
)

SELECT_JOB_COLUMNS = """
    SELECT id, kind, status, url, parent_id, playlist_id, playlist_title,
           playlist_index, playlist_entry_count, extractor_key, media_id, title,
           selected_format_id, download_options, output_path, attempt_count,
           failure_reason, failure_message
    FROM jobs
"""

INSERT_JOB = """
    INSERT INTO jobs (
        kind, status, url, parent_id, playlist_id, playlist_title,
        playlist_index, playlist_entry_count, extractor_key, media_id, title,
        selected_format_id, download_options, output_path, attempt_count,
        failure_reason, failure_message, created_at, updated_at
    ) VALUES (
        :kind, :status, :url, :parent_id, :playlist_id, :playlist_title,
        :playlist_index, :playlist_entry_count, :extractor_key, :media_id, :title,
        :selected_format_id, :download_options, :output_path, :attempt_count,
        :failure_reason, :failure_message, :now, :now
    )
"""

UPDATE_JOB = """
    UPDATE jobs SET
        kind = :kind, status = :status, url = :url, parent_id = :parent_id,
        playlist_id = :playlist_id, playlist_title = :playlist_title,
        playlist_index = :playlist_index,
        playlist_entry_count = :playlist_entry_count,
        extractor_key = :extractor_key, media_id = :media_id, title = :title,
        selected_format_id = :selected_format_id,
        download_options = :download_options, output_path = :output_path,
        attempt_count = :attempt_count, failure_reason = :failure_reason,
        failure_message = :failure_message, updated_at = :now
    WHERE id = :job_id
"""

# Mismo criterio que el índice unique_active_download_per_media.
# Misma expresión que el índice unique_active_download_per_media, para que
# SQLite lo use en la consulta.
SELECT_ACTIVE_DOWNLOAD = """
    SELECT 1 FROM jobs
    WHERE kind = 'DOWNLOAD' AND extractor_key = ? AND media_id = ?
      AND json_extract(download_options, '$.audio_only') = ?
      AND status <> 'SKIPPED'
    LIMIT 1
"""

# SQLite nombra el índice, y no las columnas, cuando incluye una expresión.
DUPLICATE_MEDIA_INDEX_MESSAGE = (
    "UNIQUE constraint failed: index 'unique_active_download_per_media'"
)
# Lo que dice SQLite cuando otra conexión retiene el bloqueo de escritura más
# allá de busy_timeout.
LOCKED_DATABASE_MESSAGE = "database is locked"
# Sobre una columna sin expresión nombra la columna (índice unique_output_path).
DUPLICATE_OUTPUT_PATH_MESSAGE = "UNIQUE constraint failed: jobs.output_path"


class SqliteJobStore:
    """Guarda los jobs en la tabla jobs de una base de datos SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Usa una conexión ya abierta con open_database."""
        self._connection = connection

    def create(self, job: Job) -> JobId:
        """Guarda un job nuevo y devuelve el identificador que se le asignó."""
        with self._connection:
            cursor = self._execute_write(INSERT_JOB, job)
        return JobId(cursor.lastrowid or 0)

    def create_many(self, jobs: Sequence[Job]) -> list[JobId]:
        """Guarda los jobs en una sola transacción, en orden.

        Si uno falla, la transacción se deshace y no queda ninguno del lote.
        """
        with self._connection:
            return [
                JobId(self._execute_write(INSERT_JOB, job).lastrowid or 0)
                for job in jobs
            ]

    def get(self, job_id: JobId) -> Job:
        """Devuelve el job guardado; JobNotFoundError si no existe."""
        row = self._connection.execute(
            f"{SELECT_JOB_COLUMNS} WHERE id = ?", (job_id,)
        ).fetchone()
        if row is None:
            raise JobNotFoundError(job_id)
        return _job_from_row(row)

    def update(self, job: Job) -> None:
        """Sustituye el job guardado por esta versión."""
        if job.job_id is None:
            message = "Job must be stored before it can be updated"
            raise ValueError(message)
        with self._connection:
            cursor = self._execute_write(UPDATE_JOB, job)
        if cursor.rowcount == 0:
            raise JobNotFoundError(job.job_id)

    def get_next_pending(self, limit: int) -> list[Job]:
        """Devuelve hasta limit jobs pendientes, en orden de creación."""
        rows = self._connection.execute(
            f"{SELECT_JOB_COLUMNS} WHERE status = ? ORDER BY id LIMIT ?",
            (JobStatus.PENDING.value, limit),
        ).fetchall()
        return [_job_from_row(row) for row in rows]

    def delete(self, job_ids: Sequence[JobId]) -> None:
        """Borra los jobs en una sola transacción (ON DELETE CASCADE)."""
        with self._connection:
            self._connection.executemany(
                "DELETE FROM jobs WHERE id = ?", [(job_id,) for job_id in job_ids]
            )

    def get_all(self) -> list[Job]:
        """Devuelve todos los jobs, en orden de creación."""
        rows = self._connection.execute(f"{SELECT_JOB_COLUMNS} ORDER BY id").fetchall()
        return [_job_from_row(row) for row in rows]

    def get_children(self, parent_id: JobId) -> list[Job]:
        """Devuelve los hijos directos de una expansión, en orden de creación."""
        rows = self._connection.execute(
            f"{SELECT_JOB_COLUMNS} WHERE parent_id = ? ORDER BY id", (parent_id,)
        ).fetchall()
        return [_job_from_row(row) for row in rows]

    def get_with_status(self, statuses: Collection[JobStatus]) -> list[Job]:
        """Devuelve los jobs en alguno de esos estados, en orden de creación."""
        status_values = [status.value for status in statuses]
        placeholders = ", ".join("?" * len(status_values))
        rows = self._connection.execute(
            f"{SELECT_JOB_COLUMNS} WHERE status IN ({placeholders}) ORDER BY id",
            status_values,
        ).fetchall()
        return [_job_from_row(row) for row in rows]

    def has_active_download(self, media_key: MediaKey, *, audio_only: bool) -> bool:
        """Indica si hay una descarga no omitida del contenido con ese tipo."""
        row = self._connection.execute(
            SELECT_ACTIVE_DOWNLOAD,
            (media_key.extractor_key, media_key.media_id, audio_only),
        ).fetchone()
        return row is not None

    def _execute_write(self, statement: str, job: Job) -> sqlite3.Cursor:
        """Ejecuta una escritura y traduce las violaciones de los índices únicos."""
        try:
            return self._connection.execute(statement, _parameters_from(job))
        except sqlite3.OperationalError as operational_error:
            if LOCKED_DATABASE_MESSAGE in str(operational_error):
                raise JobStoreLockedError(str(operational_error)) from operational_error
            raise
        except sqlite3.IntegrityError as integrity_error:
            message = str(integrity_error)
            if job.media_key is not None and DUPLICATE_MEDIA_INDEX_MESSAGE in message:
                raise DuplicateActiveDownloadError(job.media_key) from integrity_error
            if job.output_path is not None and DUPLICATE_OUTPUT_PATH_MESSAGE in message:
                raise DuplicateOutputPathError(job.output_path) from integrity_error
            raise


def _parameters_from(job: Job) -> dict[str, Any]:
    """Convierte un job en los parámetros con nombre de las sentencias SQL."""
    media_key = job.media_key
    playlist_context = job.playlist_context
    return {
        "job_id": job.job_id,
        "kind": job.kind.value,
        "status": job.status.value,
        "url": job.url,
        "parent_id": job.parent_id,
        "playlist_id": playlist_context.playlist_id if playlist_context else None,
        "playlist_title": playlist_context.playlist_title if playlist_context else None,
        "playlist_index": playlist_context.playlist_index if playlist_context else None,
        "playlist_entry_count": (
            playlist_context.playlist_entry_count if playlist_context else None
        ),
        "extractor_key": media_key.extractor_key if media_key else None,
        "media_id": media_key.media_id if media_key else None,
        "title": job.title,
        "selected_format_id": job.selected_format_id,
        "download_options": _serialize_download_options(job.download_options),
        "output_path": job.output_path,
        "attempt_count": job.attempt_count,
        "failure_reason": job.failure_reason.value if job.failure_reason else None,
        "failure_message": job.failure_message,
        "now": datetime.now(UTC).isoformat(),
    }


def _job_from_row(row: tuple[Any, ...]) -> Job:
    """Reconstruye un job a partir de una fila de SELECT_JOB_COLUMNS."""
    (
        job_id,
        kind,
        status,
        url,
        parent_id,
        playlist_id,
        playlist_title,
        playlist_index,
        playlist_entry_count,
        extractor_key,
        media_id,
        title,
        selected_format_id,
        download_options,
        output_path,
        attempt_count,
        failure_reason,
        failure_message,
    ) = row
    return Job(
        job_id=JobId(job_id),
        kind=JobKind(kind),
        status=JobStatus(status),
        url=url,
        download_options=_deserialize_download_options(download_options),
        parent_id=JobId(parent_id) if parent_id is not None else None,
        playlist_context=(
            PlaylistContext(
                playlist_id=playlist_id,
                playlist_title=playlist_title,
                playlist_index=playlist_index,
                playlist_entry_count=playlist_entry_count,
            )
            if playlist_id is not None
            else None
        ),
        media_key=MediaKey(extractor_key, media_id) if extractor_key else None,
        title=title,
        selected_format_id=selected_format_id,
        attempt_count=attempt_count,
        failure_reason=FailureReason(failure_reason) if failure_reason else None,
        failure_message=failure_message,
        output_path=output_path,
    )


def _serialize_download_options(download_options: DownloadOptions) -> str:
    """Guarda las download options como JSON (diseño, Parte 2, §2.3)."""
    return json.dumps(
        {
            "format_selector": download_options.format_selector,
            "download_directory": str(download_options.download_directory),
            "output_template": download_options.output_template,
            "audio_only": download_options.audio_only,
            "whole_playlist": download_options.whole_playlist,
        }
    )


def _deserialize_download_options(serialized: str) -> DownloadOptions:
    """Reconstruye las download options guardadas como JSON."""
    values = json.loads(serialized)
    return DownloadOptions(
        format_selector=values["format_selector"],
        download_directory=Path(values["download_directory"]),
        output_template=values["output_template"],
        audio_only=values["audio_only"],
        # Los jobs guardados antes de T43 no tienen la clave.
        whole_playlist=values.get("whole_playlist", False),
    )
