"""Caso de uso UC-06, paso 2: corregir los jobs que dejó un cierre inesperado.

Tras un corte de luz o un cierre de la terminal, ningún worker sigue con los
jobs RUNNING ni confirmará los CANCELLATION_REQUESTED. run lo corrige antes de
enviar ningún job.
"""

from dataclasses import dataclass

from queued_media_downloader.job_storage import JobStore
from queued_media_downloader.jobs import JobStatus

INTERRUPTED_STATUSES = frozenset({JobStatus.RUNNING, JobStatus.CANCELLATION_REQUESTED})


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    """Cuántos jobs volvieron a la cola y cuántos quedaron cancelados."""

    requeued_job_count: int
    cancelled_job_count: int

    @property
    def recovered_job_count(self) -> int:
        """Todos los jobs corregidos."""
        return self.requeued_job_count + self.cancelled_job_count


class RecoverInterruptedJobs:
    """Devuelve a la cola los jobs en curso y cancela los que se cancelaban."""

    def __init__(self, job_store: JobStore) -> None:
        """Usa job_store para leer y guardar los jobs."""
        self._job_store = job_store

    def execute(self) -> RecoveryResult:
        """Corrige los jobs interrumpidos; debe ejecutarse antes que la cola."""
        recovered_jobs = [
            interrupted_job.recover_from_interruption()
            for interrupted_job in self._job_store.get_with_status(INTERRUPTED_STATUSES)
        ]
        for recovered_job in recovered_jobs:
            self._job_store.update(recovered_job)
        cancelled_job_count = sum(
            job.status is JobStatus.CANCELLED for job in recovered_jobs
        )
        return RecoveryResult(
            requeued_job_count=len(recovered_jobs) - cancelled_job_count,
            cancelled_job_count=cancelled_job_count,
        )
