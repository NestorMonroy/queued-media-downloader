"""Petición de un usuario sobre un job existente (UC-05, UC-07)."""

from dataclasses import dataclass
from enum import StrEnum
from typing import NewType

from queued_media_downloader.jobs.job import JobId

JobRequestId = NewType("JobRequestId", int)


class JobRequestType(StrEnum):
    """Lo que el usuario pide sobre un job."""

    CANCEL = "CANCEL"
    RETRY = "RETRY"


@dataclass(frozen=True, slots=True, kw_only=True)
class JobRequest:
    """Una job request: cancel y retry solo las registran (diseño, Parte 2, §2.4).

    Solo el proceso de run cambia el estado de los jobs; las procesa en cada
    vuelta de la cola, o al arrancar si run no estaba activo (UC-05 A5).
    """

    job_id: JobId
    request_type: JobRequestType
    request_id: JobRequestId | None = None
