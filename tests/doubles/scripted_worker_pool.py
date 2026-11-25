"""WorkerPool en el mismo proceso que publica una secuencia predefinida."""

from collections import deque
from collections.abc import Mapping, Sequence
from enum import Enum

from queued_media_downloader.jobs import (
    Job,
    JobCancelled,
    JobEvent,
    JobId,
    JobKind,
    JobStarted,
)
from queued_media_downloader.workers import NoIdleWorkerError, WorkerMessage

ScriptKey = tuple[JobKind, str]


class ScriptPause(Enum):
    """Marcas que el guion puede poner entre los job events."""

    # El job sigue en curso hasta que se pide su cancelación: entonces publica
    # JobCancelled (cancelación cooperativa, UC-05 paso 5), salvo que el pool
    # ignore las cancelaciones (A2).
    WAIT_FOR_CANCELLATION = "wait for cancellation"


WAIT_FOR_CANCELLATION = ScriptPause.WAIT_FOR_CANCELLATION
ScriptStep = JobEvent | ScriptPause


class ScriptedWorkerPool:
    """Responde a cada job enviado con los job events del guion.

    Como el pool real, publica JobStarted antes que el guion, rechaza envíos
    sin workers libres y libera al worker con el evento final.
    """

    def __init__(
        self,
        worker_count: int,
        script: Mapping[ScriptKey, Sequence[ScriptStep]],
        *,
        ignores_cancellation: bool = False,
    ) -> None:
        """Usa worker_count workers ficticios y el guion por (tipo de job, URL)."""
        self._worker_count = worker_count
        self._script = script
        self._ignores_cancellation = ignores_cancellation
        self._busy_job_count = 0
        self._undelivered: deque[WorkerMessage] = deque()
        self._waiting_job_ids: set[JobId] = set()
        self._sequence_numbers: dict[JobId, int] = {}
        self.submitted_jobs: list[Job] = []
        self.cancellation_requests: list[JobId] = []
        self.terminated_job_ids: list[JobId] = []
        self.was_shut_down = False

    def submit(self, job: Job) -> None:
        """Encola los mensajes del guion para el job, hasta la primera pausa."""
        if self.count_idle_workers() == 0:
            raise NoIdleWorkerError
        if job.job_id is None:
            message = "Only stored jobs can be submitted"
            raise ValueError(message)
        self.submitted_jobs.append(job)
        self._busy_job_count += 1
        for step in [JobStarted(), *self._script[(job.kind, job.url)]]:
            if isinstance(step, ScriptPause):
                self._waiting_job_ids.add(job.job_id)
                return
            self._publish(job.job_id, step)

    def collect_events(self, timeout_seconds: float) -> list[WorkerMessage]:  # noqa: ARG002
        """Entrega todos los mensajes pendientes, sin esperar."""
        delivered = list(self._undelivered)
        self._undelivered.clear()
        self._busy_job_count -= sum(message.ends_the_job_run for message in delivered)
        return delivered

    def request_cancellation(self, job_id: JobId) -> None:
        """Anota la petición; un job en pausa publica JobCancelled si no se ignora."""
        self.cancellation_requests.append(job_id)
        if job_id in self._waiting_job_ids and not self._ignores_cancellation:
            self._waiting_job_ids.discard(job_id)
            self._publish(job_id, JobCancelled())

    def terminate_worker_running(self, job_id: JobId) -> bool:
        """Descarta lo que el job aún no publicó y libera su worker ficticio."""
        undelivered_of_job = [m for m in self._undelivered if m.job_id == job_id]
        if not undelivered_of_job and job_id not in self._waiting_job_ids:
            return False
        for message in undelivered_of_job:
            self._undelivered.remove(message)
        self._waiting_job_ids.discard(job_id)
        self._busy_job_count -= 1
        self.terminated_job_ids.append(job_id)
        return True

    def count_idle_workers(self) -> int:
        """Workers ficticios sin job asignado."""
        return self._worker_count - self._busy_job_count

    def shut_down(self) -> None:
        """Registra que se apagó."""
        self.was_shut_down = True

    def _publish(self, job_id: JobId, job_event: JobEvent) -> None:
        sequence_number = self._sequence_numbers.get(job_id, 0) + 1
        self._sequence_numbers[job_id] = sequence_number
        self._undelivered.append(
            WorkerMessage(
                worker_id=1,
                job_id=job_id,
                sequence_number=sequence_number,
                job_event=job_event,
            )
        )
