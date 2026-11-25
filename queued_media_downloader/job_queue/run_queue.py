"""Caso de uso UC-03: ejecutar la cola hasta que no queden jobs pendientes."""

import time
from collections.abc import Callable
from dataclasses import dataclass

from queued_media_downloader.job_queue.job_event_applier import JobEventApplier
from queued_media_downloader.job_storage import JobRequestInbox, JobStore
from queued_media_downloader.jobs import (
    Job,
    JobCancelled,
    JobId,
    JobKind,
    JobRequest,
    JobRequestType,
    JobStatus,
)
from queued_media_downloader.workers import (
    POOL_SEQUENCE_NUMBER,
    POOL_WORKER_ID,
    WorkerMessage,
    WorkerPool,
)

# Espera máxima por los mensajes de los workers en cada vuelta del bucle; acota
# cuánto tarda en enviarse un job nuevo cuando se libera un worker.
COLLECT_TIMEOUT_SECONDS = 0.5
# Espera por defecto antes de terminar un worker que no confirma la cancelación.
DEFAULT_CANCELLATION_GRACE_SECONDS = 10.0

# Recibe cada mensaje y el job tal como quedó (None si el mensaje solo informa
# del avance), para que la presentación sepa, por ejemplo, si quedó SKIPPED.
Present = Callable[[WorkerMessage, Job | None], None]


# Recibe cada job request procesada y el job tal como quedó.
PresentJobRequest = Callable[[JobRequest, Job], None]


def present_nothing(message: WorkerMessage, job: Job | None) -> None:
    """Presentación por defecto: no muestra nada."""


def present_no_job_request(job_request: JobRequest, job: Job) -> None:
    """Presentación por defecto de las job requests: no muestra nada."""


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
        job_request_inbox: JobRequestInbox,
        present: Present = present_nothing,
        present_job_request: PresentJobRequest = present_no_job_request,
        cancellation_grace_seconds: float = DEFAULT_CANCELLATION_GRACE_SECONDS,
    ) -> None:
        """Usa job_store, worker_pool y la bandeja de job requests.

        present recibe cada mensaje ya aplicado; present_job_request, cada job
        request procesada. Un worker que no confirma una cancelación en
        cancellation_grace_seconds se termina con su árbol (UC-05 A2).
        """
        self._job_store = job_store
        self._worker_pool = worker_pool
        self._job_request_inbox = job_request_inbox
        self._present = present
        self._present_job_request = present_job_request
        self._job_event_applier = JobEventApplier(job_store)
        self._cancellation_grace_seconds = cancellation_grace_seconds
        self._running_job_ids: set[JobId] = set()
        self._cancellation_deadlines: dict[JobId, float] = {}

    def execute(self) -> RunQueueResult:
        """Ejecuta jobs hasta que no queden pendientes ni en curso.

        Un job de expansión que encuentra un contenido vuelve a la cola como
        descarga, así que la cola puede crecer mientras se ejecuta.
        """
        failed_job_count = 0
        while True:
            # Antes de enviar nada: un job cancelado no debe llegar a un worker.
            self._process_job_requests()
            self._terminate_unconfirmed_cancellations()
            self._submit_pending_jobs()
            if not self._running_job_ids:
                return RunQueueResult(failed_job_count=failed_job_count)
            for message in self._worker_pool.collect_events(COLLECT_TIMEOUT_SECONDS):
                failed_job_count += self._apply(message)

    def _apply(self, message: WorkerMessage) -> int:
        """Aplica y presenta un mensaje; devuelve 1 si dejó el job FAILED.

        Se cuenta el estado que quedó guardado, no el job event: un JobCompleted
        puede dejar el job FAILED (T44). Los jobs en curso son un conjunto: un
        mensaje final tardío de un job ya terminado no descuenta dos veces.
        """
        updated_job = self._job_event_applier.apply(message)
        self._present(message, updated_job)
        if message.ends_the_job_run:
            self._running_job_ids.discard(message.job_id)
            self._cancellation_deadlines.pop(message.job_id, None)
        return int(updated_job is not None and updated_job.status is JobStatus.FAILED)

    def _terminate_unconfirmed_cancellations(self) -> None:
        """Termina el árbol de los workers que no confirmaron a tiempo (A2).

        El pool no publica nada por el job terminado: RunQueue aplica un
        JobCancelled en su nombre, como hace el pool con un worker caído.
        """
        now = time.monotonic()
        expired = [j for j, d in self._cancellation_deadlines.items() if d <= now]
        for job_id in expired:
            del self._cancellation_deadlines[job_id]
            if self._worker_pool.terminate_worker_running(job_id):
                self._apply(
                    WorkerMessage(
                        worker_id=POOL_WORKER_ID,
                        job_id=job_id,
                        sequence_number=POOL_SEQUENCE_NUMBER,
                        job_event=JobCancelled(),
                    )
                )

    def _process_job_requests(self) -> None:
        """Aplica las job requests CANCEL pendientes (UC-05, pasos 3 a 7).

        Las RETRY las procesa el caso de uso de reintento (UC-07).
        """
        for job_request in self._job_request_inbox.get_unprocessed():
            if job_request.request_type is not JobRequestType.CANCEL:
                continue
            cancelled_job = self._cancel(self._job_store.get(job_request.job_id))
            assert job_request.request_id is not None
            self._job_request_inbox.mark_processed(job_request.request_id)
            self._present_job_request(job_request, cancelled_job)

    def _cancel(self, job: Job) -> Job:
        """Cancela el job, y si es una expansión, sus descendientes no terminados.

        Un job PENDING se cancela ya (A1); uno RUNNING pasa a
        CANCELLATION_REQUESTED y se pide al worker que lo detenga. Uno ya
        terminado o ya cancelándose no cambia (A7).
        """
        if job.status is JobStatus.PENDING:
            job = job.transition_to(JobStatus.CANCELLED)
            self._job_store.update(job)
        elif job.status is JobStatus.RUNNING:
            job = job.transition_to(JobStatus.CANCELLATION_REQUESTED)
            self._job_store.update(job)
            assert job.job_id is not None
            self._worker_pool.request_cancellation(job.job_id)
            self._cancellation_deadlines[job.job_id] = (
                time.monotonic() + self._cancellation_grace_seconds
            )
        if job.kind is JobKind.EXPANSION and job.job_id is not None:
            # Hijos creados después de registrar la petición (A4).
            for child in self._job_store.get_children(job.job_id):
                if not child.is_finished():
                    self._cancel(child)
        return job

    def _submit_pending_jobs(self) -> None:
        """Envía un job pendiente por worker libre.

        El job pasa a RUNNING antes de enviarse, para que la siguiente consulta
        de pendientes no lo vuelva a tomar.
        """
        idle_worker_count = self._worker_pool.count_idle_workers()
        if idle_worker_count == 0:
            return
        pending_jobs = self._job_store.get_next_pending(idle_worker_count)
        for pending_job in pending_jobs:
            running_job = pending_job.start()
            self._job_store.update(running_job)
            self._worker_pool.submit(running_job)
            assert running_job.job_id is not None
            self._running_job_ids.add(running_job.job_id)
