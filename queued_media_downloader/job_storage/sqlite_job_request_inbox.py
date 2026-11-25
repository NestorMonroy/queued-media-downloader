"""JobRequestInbox sobre la tabla job_requests de SQLite."""

import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime

from queued_media_downloader.job_storage.job_store import JobNotFoundError
from queued_media_downloader.jobs import (
    JobId,
    JobRequest,
    JobRequestId,
    JobRequestType,
)

INSERT_JOB_REQUEST = """
    INSERT INTO job_requests (job_id, request_type, requested_at)
    VALUES (?, ?, ?)
"""
SELECT_UNPROCESSED = """
    SELECT id, job_id, request_type FROM job_requests
    WHERE processed_at IS NULL ORDER BY id
"""
MARK_PROCESSED = "UPDATE job_requests SET processed_at = ? WHERE id = ?"


class SqliteJobRequestInbox:
    """Bandeja de job requests en la misma base de datos que los jobs."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Usa connection, ya abierta con open_database."""
        self._connection = connection

    def create_many(self, job_requests: Sequence[JobRequest]) -> list[JobRequestId]:
        """Guarda las job requests en una sola transacción, en orden."""
        requested_at = datetime.now(UTC).isoformat()
        request_ids: list[JobRequestId] = []
        with self._connection:
            for job_request in job_requests:
                try:
                    cursor = self._connection.execute(
                        INSERT_JOB_REQUEST,
                        (
                            job_request.job_id,
                            job_request.request_type.value,
                            requested_at,
                        ),
                    )
                except sqlite3.IntegrityError as integrity_error:
                    raise JobNotFoundError(job_request.job_id) from integrity_error
                assert cursor.lastrowid is not None
                request_ids.append(JobRequestId(cursor.lastrowid))
        return request_ids

    def get_unprocessed(self) -> list[JobRequest]:
        """Devuelve las job requests aún sin procesar, en orden de llegada."""
        rows = self._connection.execute(SELECT_UNPROCESSED).fetchall()
        return [
            JobRequest(
                request_id=JobRequestId(request_id),
                job_id=JobId(job_id),
                request_type=JobRequestType(request_type),
            )
            for request_id, job_id, request_type in rows
        ]

    def mark_processed(self, request_id: JobRequestId) -> None:
        """Marca procesada una job request."""
        with self._connection:
            self._connection.execute(
                MARK_PROCESSED, (datetime.now(UTC).isoformat(), request_id)
            )
