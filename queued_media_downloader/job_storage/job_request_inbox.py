"""Contrato de la bandeja de job requests (diseño, Parte 1, §4)."""

from collections.abc import Sequence
from typing import Protocol

from queued_media_downloader.jobs import JobRequest, JobRequestId


class JobRequestInbox(Protocol):
    """Guarda las job requests de cancel y retry hasta que run las procesa.

    Separada de JobStore (segregación de interfaces): cancel y retry solo
    registran peticiones; nunca cambian el estado de un job.
    """

    def create_many(self, job_requests: Sequence[JobRequest]) -> list[JobRequestId]:
        """Guarda las job requests en una sola transacción, en orden.

        Raises:
            JobNotFoundError: Si alguna se refiere a un job que no existe; no
                se guarda ninguna.
        """
        ...

    def get_unprocessed(self) -> list[JobRequest]:
        """Devuelve las job requests aún sin procesar, en orden de llegada."""
        ...

    def mark_processed(self, request_id: JobRequestId) -> None:
        """Marca procesada una job request; no vuelve a devolverse."""
        ...
