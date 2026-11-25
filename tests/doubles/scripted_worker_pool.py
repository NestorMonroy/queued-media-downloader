"""WorkerPool en el mismo proceso que publica una secuencia predefinida."""

from collections import deque
from collections.abc import Mapping, Sequence

from queued_media_downloader.jobs import Job, JobEvent, JobId, JobKind, JobStarted
from queued_media_downloader.workers import NoIdleWorkerError, WorkerMessage

ScriptKey = tuple[JobKind, str]


class ScriptedWorkerPool:
    """Responde a cada job enviado con los job events del guion.

    Como el pool real, publica JobStarted antes que el guion, rechaza envíos
    sin workers libres y libera al worker con el evento final.
    """

    def __init__(
        self, worker_count: int, script: Mapping[ScriptKey, Sequence[JobEvent]]
    ) -> None:
        """Usa worker_count workers ficticios y el guion por (tipo de job, URL)."""
        self._worker_count = worker_count
        self._script = script
        self._busy_job_count = 0
        self._undelivered: deque[WorkerMessage] = deque()
        self.submitted_jobs: list[Job] = []
        self.terminated_job_ids: list[JobId] = []
        self.was_shut_down = False

    def submit(self, job: Job) -> None:
        """Encola los mensajes del guion para el job."""
        if self.count_idle_workers() == 0:
            raise NoIdleWorkerError
        if job.job_id is None:
            message = "Only stored jobs can be submitted"
            raise ValueError(message)
        self.submitted_jobs.append(job)
        self._busy_job_count += 1
        job_events = [JobStarted(), *self._script[(job.kind, job.url)]]
        for sequence_number, job_event in enumerate(job_events, start=1):
            self._undelivered.append(
                WorkerMessage(
                    worker_id=1,
                    job_id=job.job_id,
                    sequence_number=sequence_number,
                    job_event=job_event,
                )
            )

    def collect_events(self, timeout_seconds: float) -> list[WorkerMessage]:  # noqa: ARG002
        """Entrega todos los mensajes pendientes, sin esperar."""
        delivered = list(self._undelivered)
        self._undelivered.clear()
        self._busy_job_count -= sum(message.ends_the_job_run for message in delivered)
        return delivered

    def terminate_worker_running(self, job_id: JobId) -> bool:
        """Descarta lo que el job aún no publicó y libera su worker ficticio."""
        undelivered_of_job = [m for m in self._undelivered if m.job_id == job_id]
        if not undelivered_of_job:
            return False
        for message in undelivered_of_job:
            self._undelivered.remove(message)
        self._busy_job_count -= 1
        self.terminated_job_ids.append(job_id)
        return True

    def count_idle_workers(self) -> int:
        """Workers ficticios sin job asignado."""
        return self._worker_count - self._busy_job_count

    def shut_down(self) -> None:
        """Registra que se apagó."""
        self.was_shut_down = True
