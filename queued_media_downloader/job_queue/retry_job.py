"""Caso de uso UC-07: registrar el reintento de jobs.

Como cancel, retry solo registra job requests; run las procesa.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from queued_media_downloader.job_storage import JobRequestInbox, JobStore
from queued_media_downloader.jobs import (
    Job,
    JobId,
    JobKind,
    JobRequest,
    JobRequestType,
    JobStatus,
)


@dataclass(frozen=True, slots=True)
class RetryJobResult:
    """Qué se registró y qué no se puede reintentar."""

    requested: list[JobId]
    not_retriable: list[Job]


class RetryJob:
    """Registra una job request RETRY por job FAILED o CANCELLED."""

    def __init__(self, job_store: JobStore, job_request_inbox: JobRequestInbox) -> None:
        """Lee los jobs de job_store y registra en job_request_inbox."""
        self._job_store = job_store
        self._job_request_inbox = job_request_inbox

    def execute(self, job_ids: Sequence[JobId]) -> RetryJobResult:
        """Registra los reintentos en una sola transacción.

        Raises:
            JobNotFoundError: Si algún job no existe; no se registra nada.
        """
        return self._register([self._job_store.get(job_id) for job_id in job_ids])

    def execute_all_failed(self) -> RetryJobResult:
        """Registra el reintento de todos los jobs FAILED (--all-failed)."""
        return self._register(self._job_store.get_with_status({JobStatus.FAILED}))

    def _register(self, jobs: Sequence[Job]) -> RetryJobResult:
        requested = [job.job_id for job in jobs if job.can_be_retried()]
        self._job_request_inbox.create_many(
            [
                JobRequest(job_id=job_id, request_type=JobRequestType.RETRY)
                for job_id in dict.fromkeys(requested)
                if job_id is not None
            ]
        )
        return RetryJobResult(
            requested=[job_id for job_id in requested if job_id is not None],
            not_retriable=[job for job in jobs if not job.can_be_retried()],
        )


def retriable_descendants(job_store: JobStore, job: Job) -> Iterator[Job]:
    """Descendientes FAILED o CANCELLED de una expansión, en profundidad.

    Al reintentar una playlist, sus hijos cancelados o fallidos vuelven con
    ella: la nueva expansión los toma por duplicados y no los recrea.
    """
    if job.kind is not JobKind.EXPANSION or job.job_id is None:
        return
    for child in job_store.get_children(job.job_id):
        if child.can_be_retried():
            yield child
        yield from retriable_descendants(job_store, child)
