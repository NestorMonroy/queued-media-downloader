"""Casos de uso UC-08 y UC-09: consultar la cola sin modificar nada."""

from collections import Counter
from dataclasses import dataclass

from queued_media_downloader.job_storage import JobStore
from queued_media_downloader.jobs import Job, JobId, JobKind, JobStatus


class ListJobs:
    """Lista los jobs, opcionalmente por estado o por playlist padre (UC-08)."""

    def __init__(self, job_store: JobStore) -> None:
        """Lee los jobs de job_store."""
        self._job_store = job_store

    def execute(
        self, status: JobStatus | None = None, parent_id: JobId | None = None
    ) -> list[Job]:
        """Devuelve los jobs que cumplen los filtros, en orden de creación.

        Raises:
            JobNotFoundError: Si parent_id no existe.
        """
        if parent_id is not None:
            self._job_store.get(parent_id)
            jobs = self._job_store.get_children(parent_id)
        elif status is not None:
            return self._job_store.get_with_status({status})
        else:
            jobs = self._job_store.get_all()
        return [job for job in jobs if status is None or job.status is status]


@dataclass(frozen=True, slots=True)
class JobDetails:
    """Un job y, si es una playlist, cuántos hijos tiene en cada estado."""

    job: Job
    children_by_status: dict[JobStatus, int]


class ShowJob:
    """Muestra todos los datos de un job (UC-09)."""

    def __init__(self, job_store: JobStore) -> None:
        """Lee los jobs de job_store."""
        self._job_store = job_store

    def execute(self, job_id: JobId) -> JobDetails:
        """Devuelve el job y el resumen de sus hijos directos por estado.

        Raises:
            JobNotFoundError: Si el job no existe.
        """
        job = self._job_store.get(job_id)
        children_by_status: dict[JobStatus, int] = {}
        if job.kind is JobKind.EXPANSION:
            counts = Counter(c.status for c in self._job_store.get_children(job_id))
            children_by_status = dict(sorted(counts.items()))
        return JobDetails(job=job, children_by_status=children_by_status)
