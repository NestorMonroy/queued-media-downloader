"""Mensaje con el que un worker publica un job event (diseño, Parte 2, §3.1)."""

from dataclasses import dataclass

from queued_media_downloader.jobs import (
    JobCancelled,
    JobCompleted,
    JobEvent,
    JobFailed,
    JobId,
    SingleMediaFound,
)

# Job events con los que el worker termina de ejecutar un job y queda libre.
# SingleMediaFound también: el job vuelve a la cola como descarga.
FINAL_JOB_EVENT_TYPES = (SingleMediaFound, JobCompleted, JobFailed, JobCancelled)

# Número de secuencia de los mensajes que el pool publica en nombre de un
# worker caído; los del worker empiezan en 1.
POOL_SEQUENCE_NUMBER = 0
# worker_id de los mensajes que la cola aplica en nombre de un worker ya
# terminado (UC-05 A2); los workers empiezan en 1.
POOL_WORKER_ID = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkerMessage:
    """Un job event con el job al que se refiere y el worker que lo publicó.

    sequence_number cuenta los mensajes de cada worker, para detectar en los
    logs mensajes perdidos o desordenados.
    """

    worker_id: int
    job_id: JobId
    sequence_number: int
    job_event: JobEvent

    @property
    def ends_the_job_run(self) -> bool:
        """Indica si el worker terminó con el job y queda libre."""
        return isinstance(self.job_event, FINAL_JOB_EVENT_TYPES)
