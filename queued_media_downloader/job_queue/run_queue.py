"""Caso de uso UC-03: ejecutar la cola hasta que no queden jobs pendientes."""

from collections.abc import Callable
from dataclasses import dataclass

from queued_media_downloader.job_queue.job_event_applier import JobEventApplier
from queued_media_downloader.job_storage import JobStore
from queued_media_downloader.jobs import Job, JobStatus
from queued_media_downloader.workers import WorkerMessage, WorkerPool

# Espera máxima por los mensajes de los workers en cada vuelta del bucle; acota
# cuánto tarda en enviarse un job nuevo cuando se libera un worker.
COLLECT_TIMEOUT_SECONDS = 0.5

# Recibe cada mensaje y el job tal como quedó (None si el mensaje solo informa
# del avance), para que la presentación sepa, por ejemplo, si quedó SKIPPED.
Present = Callable[[WorkerMessage, Job | None], None]


def present_nothing(message: WorkerMessage, job: Job | None) -> None:
    """Presentación por defecto: no muestra nada."""


@dataclass(frozen=True, slots=True)
class RunQueueResult:
    """Resultado de una ejecución de la cola; decide el código de salida."""

    failed_job_count: int


class RunQueue:
    """Envía los jobs pendientes a los workers libres y aplica lo que publican.

    El pool lo crea y lo apaga quien crea RunQueue.
    """

    def __init__(
        self,
        job_store: JobStore,
        worker_pool: WorkerPool,
        present: Present = present_nothing,
    ) -> None:
        """Usa job_store y worker_pool; present recibe cada mensaje ya aplicado."""
        self._job_store = job_store
        self._worker_pool = worker_pool
        self._present = present
        self._job_event_applier = JobEventApplier(job_store)

    def execute(self) -> RunQueueResult:
        """Ejecuta jobs hasta que no queden pendientes ni en curso.

        Un job de expansión que encuentra un contenido vuelve a la cola como
        descarga, así que la cola puede crecer mientras se ejecuta.
        """
        running_job_count = 0
        failed_job_count = 0
        while True:
            running_job_count += self._submit_pending_jobs()
            if running_job_count == 0:
                return RunQueueResult(failed_job_count=failed_job_count)
            for message in self._worker_pool.collect_events(COLLECT_TIMEOUT_SECONDS):
                updated_job = self._job_event_applier.apply(message)
                self._present(message, updated_job)
                running_job_count -= message.ends_the_job_run
                # Se cuenta el estado que quedó guardado, no el job event: un
                # JobCompleted puede dejar el job FAILED (T44).
                failed_job_count += (
                    updated_job is not None and updated_job.status is JobStatus.FAILED
                )

    def _submit_pending_jobs(self) -> int:
        """Envía un job pendiente por worker libre; devuelve cuántos envió.

        El job pasa a RUNNING antes de enviarse, para que la siguiente consulta
        de pendientes no lo vuelva a tomar.
        """
        idle_worker_count = self._worker_pool.count_idle_workers()
        if idle_worker_count == 0:
            return 0
        pending_jobs = self._job_store.get_next_pending(idle_worker_count)
        for pending_job in pending_jobs:
            running_job = pending_job.start()
            self._job_store.update(running_job)
            self._worker_pool.submit(running_job)
        return len(pending_jobs)
