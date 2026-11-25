"""Caso de uso UC-05, pasos 1 y 2: registrar la cancelación de jobs.

cancel solo registra job requests; el proceso de run las procesa y cambia los
estados (diseño, Parte 2, §2.4). Así funciona con run activo en otra terminal
y también sin él: la petición espera al siguiente run (A5).
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
)


@dataclass(frozen=True, slots=True)
class CancelJobResult:
    """Qué se registró y qué no hacía falta cancelar."""

    # Jobs pedidos con su número de descendientes no terminados (A4).
    requested: dict[JobId, int]
    # Jobs pedidos que ya habían terminado (A7): no se registra nada.
    already_finished: list[Job]


class CancelJob:
    """Registra una job request CANCEL por job, y por sus descendientes."""

    def __init__(self, job_store: JobStore, job_request_inbox: JobRequestInbox) -> None:
        """Lee los jobs de job_store y registra en job_request_inbox."""
        self._job_store = job_store
        self._job_request_inbox = job_request_inbox

    def execute(self, job_ids: Sequence[JobId]) -> CancelJobResult:
        """Registra las cancelaciones en una sola transacción.

        Una expansión arrastra a todos sus descendientes no terminados (A4),
        también los de sus playlists anidadas.

        Raises:
            JobNotFoundError: Si algún job no existe; no se registra nada.
        """
        jobs = [self._job_store.get(job_id) for job_id in job_ids]
        requested: dict[JobId, int] = {}
        already_finished: list[Job] = []
        cancelled_job_ids: dict[JobId, None] = {}
        for job in jobs:
            assert job.job_id is not None
            if job.is_finished():
                already_finished.append(job)
                continue
            descendant_ids = [d.job_id for d in self._unfinished_descendants(job)]
            requested[job.job_id] = len(descendant_ids)
            for job_id in (job.job_id, *descendant_ids):
                if job_id is not None:
                    cancelled_job_ids[job_id] = None
        self._job_request_inbox.create_many(
            [
                JobRequest(job_id=job_id, request_type=JobRequestType.CANCEL)
                for job_id in cancelled_job_ids
            ]
        )
        return CancelJobResult(requested=requested, already_finished=already_finished)

    def _unfinished_descendants(self, job: Job) -> Iterator[Job]:
        """Descendientes no terminados de una expansión, en profundidad."""
        if job.kind is not JobKind.EXPANSION or job.job_id is None:
            return
        for child in self._job_store.get_children(job.job_id):
            if not child.is_finished():
                yield child
            yield from self._unfinished_descendants(child)
