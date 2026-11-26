"""Espera a que la cola quede libre en lugar de fallar (proceso de run).

Los comandos cortos (enqueue, cancel, retry, purge) informan de una cola
ocupada más allá de busy_timeout y terminan sin cambiar nada (UC-02 A3). run,
en cambio, es el proceso largo de la cola: abandonarla dejaría los jobs en curso
RUNNING y sus workers cortados a mitad de la descarga o de la unión (T42-D12).
Con estos envoltorios, cada operación de run se repite hasta que el otro
programa suelta el bloqueo; un segundo Ctrl+C sigue deteniendo run.

Repetir una operación es seguro: cada escritura es una transacción, y SQLite
la deshace entera cuando no consigue el bloqueo.
"""

import sqlite3
from collections.abc import Callable, Collection, Sequence
from typing import TypeVar

from queued_media_downloader.job_storage.job_request_inbox import JobRequestInbox
from queued_media_downloader.job_storage.job_store import (
    JobStore,
    JobStoreLockedError,
)
from queued_media_downloader.job_storage.sqlite_job_store import (
    LOCKED_DATABASE_MESSAGE,
)
from queued_media_downloader.jobs import (
    Job,
    JobId,
    JobRequest,
    JobRequestId,
    JobStatus,
    MediaKey,
)

Result = TypeVar("Result")


class BusyQueueWaiting:
    """Repite una operación mientras la base de datos esté bloqueada."""

    def __init__(self, report_busy_queue: Callable[[], None]) -> None:
        """Llama a report_busy_queue cada vez que empieza una espera."""
        self._report_busy_queue = report_busy_queue

    def run(self, operation: Callable[[], Result]) -> Result:
        """Resultado de operation, cuando la cola quede libre.

        Cada intento ya espera busy_timeout dentro de SQLite: entre intentos
        no hace falta otra pausa.
        """
        is_waiting = False
        while True:
            try:
                return operation()
            except (JobStoreLockedError, sqlite3.OperationalError) as error:
                if not _is_locked_database(error):
                    raise
                if not is_waiting:
                    self._report_busy_queue()
                    is_waiting = True


class BusyQueueWaitingJobStore:
    """JobStore que espera a que la cola quede libre (ver el módulo)."""

    def __init__(self, job_store: JobStore, waiting: BusyQueueWaiting) -> None:
        """Delega en job_store y repite con waiting."""
        self._job_store = job_store
        self._waiting = waiting

    def create(self, job: Job) -> JobId:
        """Como JobStore.create."""
        return self._waiting.run(lambda: self._job_store.create(job))

    def create_many(self, jobs: Sequence[Job]) -> list[JobId]:
        """Como JobStore.create_many."""
        return self._waiting.run(lambda: self._job_store.create_many(jobs))

    def get(self, job_id: JobId) -> Job:
        """Como JobStore.get."""
        return self._waiting.run(lambda: self._job_store.get(job_id))

    def update(self, job: Job) -> None:
        """Como JobStore.update."""
        self._waiting.run(lambda: self._job_store.update(job))

    def get_next_pending(self, limit: int) -> list[Job]:
        """Como JobStore.get_next_pending."""
        return self._waiting.run(lambda: self._job_store.get_next_pending(limit))

    def delete(self, job_ids: Sequence[JobId]) -> None:
        """Como JobStore.delete."""
        self._waiting.run(lambda: self._job_store.delete(job_ids))

    def get_all(self) -> list[Job]:
        """Como JobStore.get_all."""
        return self._waiting.run(self._job_store.get_all)

    def get_children(self, parent_id: JobId) -> list[Job]:
        """Como JobStore.get_children."""
        return self._waiting.run(lambda: self._job_store.get_children(parent_id))

    def get_with_status(self, statuses: Collection[JobStatus]) -> list[Job]:
        """Como JobStore.get_with_status."""
        return self._waiting.run(lambda: self._job_store.get_with_status(statuses))

    def has_active_download(self, media_key: MediaKey, *, audio_only: bool) -> bool:
        """Como JobStore.has_active_download."""
        return self._waiting.run(
            lambda: self._job_store.has_active_download(
                media_key, audio_only=audio_only
            )
        )


class BusyQueueWaitingJobRequestInbox:
    """JobRequestInbox que espera a que la cola quede libre (ver el módulo)."""

    def __init__(
        self, job_request_inbox: JobRequestInbox, waiting: BusyQueueWaiting
    ) -> None:
        """Delega en job_request_inbox y repite con waiting."""
        self._job_request_inbox = job_request_inbox
        self._waiting = waiting

    def create_many(self, job_requests: Sequence[JobRequest]) -> list[JobRequestId]:
        """Como JobRequestInbox.create_many."""
        return self._waiting.run(
            lambda: self._job_request_inbox.create_many(job_requests)
        )

    def get_unprocessed(self) -> list[JobRequest]:
        """Como JobRequestInbox.get_unprocessed."""
        return self._waiting.run(self._job_request_inbox.get_unprocessed)

    def mark_processed(self, request_id: JobRequestId) -> None:
        """Como JobRequestInbox.mark_processed."""
        self._waiting.run(lambda: self._job_request_inbox.mark_processed(request_id))


def _is_locked_database(error: Exception) -> bool:
    """Bloqueo de otro proceso, no otro fallo de SQLite."""
    return isinstance(error, JobStoreLockedError) or (
        LOCKED_DATABASE_MESSAGE in str(error)
    )
