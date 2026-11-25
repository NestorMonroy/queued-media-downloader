"""JobRequestInbox en memoria para las pruebas de los casos de uso."""

from collections.abc import Sequence
from dataclasses import replace

from queued_media_downloader.job_storage import JobStore
from queued_media_downloader.jobs import JobRequest, JobRequestId


class InMemoryJobRequestInbox:
    """Guarda las job requests en una lista; comprueba que el job exista."""

    def __init__(self, job_store: JobStore) -> None:
        """Usa job_store para la misma comprobación que la clave foránea."""
        self._job_store = job_store
        self._requests: list[JobRequest] = []
        self._processed: set[JobRequestId] = set()

    def create_many(self, job_requests: Sequence[JobRequest]) -> list[JobRequestId]:
        """Guarda todas o ninguna."""
        for job_request in job_requests:
            self._job_store.get(job_request.job_id)  # JobNotFoundError
        stored = [
            replace(job_request, request_id=JobRequestId(len(self._requests) + n))
            for n, job_request in enumerate(job_requests, start=1)
        ]
        self._requests.extend(stored)
        return [JobRequestId(int(request.request_id or 0)) for request in stored]

    def get_unprocessed(self) -> list[JobRequest]:
        """Las que aún no se marcaron procesadas, en orden."""
        return [r for r in self._requests if r.request_id not in self._processed]

    def mark_processed(self, request_id: JobRequestId) -> None:
        """La marca procesada."""
        self._processed.add(request_id)

    def all_requests(self) -> list[JobRequest]:
        """Todas, procesadas o no (solo para pruebas)."""
        return list(self._requests)
