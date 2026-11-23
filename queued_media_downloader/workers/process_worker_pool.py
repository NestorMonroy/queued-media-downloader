"""WorkerPool con un proceso por worker, arrancado con spawn (ADR-0008).

spawn es el único método de arranque en Windows; usarlo en todos los sistemas
hace que las pruebas de cualquier sistema ejerciten el mismo camino.
"""

import itertools
import logging
import multiprocessing
import queue
from collections.abc import Callable
from dataclasses import dataclass
from logging import LogRecord
from multiprocessing.context import SpawnProcess
from multiprocessing.queues import Queue

from queued_media_downloader.jobs import FailureReason, Job, JobFailed, JobId
from queued_media_downloader.media_extraction import MediaSource
from queued_media_downloader.workers.process_queue_receiver import (
    ProcessQueueReceiver,
)
from queued_media_downloader.workers.worker_instructions import (
    RunJob,
    ShutDown,
    WorkerInstruction,
)
from queued_media_downloader.workers.worker_logging import forward_log_record
from queued_media_downloader.workers.worker_loop import worker_loop
from queued_media_downloader.workers.worker_message import (
    POOL_SEQUENCE_NUMBER,
    WorkerMessage,
)
from queued_media_downloader.workers.worker_pool import NoIdleWorkerError

logger = logging.getLogger(__name__)

SHUT_DOWN_TIMEOUT_SECONDS = 10.0


@dataclass(slots=True)
class WorkerHandle:
    """Lo que el proceso principal sabe de un worker."""

    worker_id: int
    process: SpawnProcess
    instruction_queue: "Queue[WorkerInstruction]"
    message_receiver: ProcessQueueReceiver
    log_record_receiver: ProcessQueueReceiver
    assigned_job_id: JobId | None = None

    def stop_receivers(self) -> None:
        """Recoge lo que el worker dejó en sus colas y deja de recibir."""
        self.message_receiver.stop()
        self.log_record_receiver.stop()


class ProcessWorkerPool:
    """Ejecuta cada job en uno de worker_count procesos.

    Cada worker tiene sus propias colas de instrucciones, mensajes y registros
    de logging (diseño, Parte 2, §3.1). Un hilo por cola pasa los mensajes a una
    cola de este proceso y los registros al logging de este proceso.
    """

    def __init__(
        self, worker_count: int, media_source_factory: Callable[[], MediaSource]
    ) -> None:
        """Arranca worker_count workers.

        Args:
            worker_count: Número de workers.
            media_source_factory: Crea la MediaSource dentro de cada worker;
                debe poder enviarse con pickle a otro proceso.
        """
        self._context = multiprocessing.get_context("spawn")
        self._media_source_factory = media_source_factory
        self._received_messages: queue.Queue[WorkerMessage] = queue.Queue()
        self._worker_ids = itertools.count(1)
        self._workers = [self._start_worker() for _ in range(worker_count)]

    def submit(self, job: Job) -> None:
        """Envía el job a un worker libre; NoIdleWorkerError si no hay ninguno."""
        idle_worker = next(
            (worker for worker in self._workers if worker.assigned_job_id is None),
            None,
        )
        if idle_worker is None:
            raise NoIdleWorkerError
        idle_worker.assigned_job_id = job.job_id
        idle_worker.instruction_queue.put(RunJob(job))

    def collect_events(self, timeout_seconds: float) -> list[WorkerMessage]:
        """Devuelve los mensajes recibidos y los de los workers caídos."""
        messages = self._receive_messages(timeout_seconds)
        self._release_finished_workers(messages)
        messages.extend(self._replace_crashed_workers())
        return messages

    def count_idle_workers(self) -> int:
        """Número de workers sin job asignado."""
        return sum(worker.assigned_job_id is None for worker in self._workers)

    def shut_down(self) -> None:
        """Pide a cada worker que termine y fuerza a los que no lo hagan a tiempo."""
        for worker in self._workers:
            if worker.process.is_alive():
                worker.instruction_queue.put(ShutDown())
        for worker in self._workers:
            worker.process.join(SHUT_DOWN_TIMEOUT_SECONDS)
            if worker.process.is_alive():
                logger.warning("Worker %s did not stop; killing it", worker.worker_id)
                worker.process.kill()
                worker.process.join()
            # Tras la salida del worker: así llegan sus últimos registros.
            worker.stop_receivers()
        self._workers = []

    def _start_worker(self) -> WorkerHandle:
        """Arranca un proceso worker con sus colas y los hilos que las reciben."""
        worker_id = next(self._worker_ids)
        worker_name = f"worker-{worker_id}"
        instruction_queue: Queue[WorkerInstruction] = self._context.Queue()
        message_queue: Queue[WorkerMessage] = self._context.Queue()
        log_queue: Queue[LogRecord] = self._context.Queue()
        process = self._context.Process(
            target=worker_loop,
            args=(
                worker_id,
                self._media_source_factory,
                instruction_queue,
                message_queue,
                log_queue,
            ),
            name=worker_name,
            daemon=True,
        )
        process.start()
        return WorkerHandle(
            worker_id,
            process,
            instruction_queue,
            message_receiver=ProcessQueueReceiver(
                message_queue,
                self._received_messages.put,
                f"{worker_name}-message-receiver",
            ),
            log_record_receiver=ProcessQueueReceiver(
                log_queue, forward_log_record, f"{worker_name}-log-receiver"
            ),
        )

    def _receive_messages(self, timeout_seconds: float) -> list[WorkerMessage]:
        """Espera el primer mensaje hasta timeout_seconds y toma los ya llegados."""
        try:
            messages = [self._received_messages.get(timeout=timeout_seconds)]
        except queue.Empty:
            return []
        return messages + self._take_received_messages()

    def _take_received_messages(self) -> list[WorkerMessage]:
        """Mensajes ya recibidos, sin esperar."""
        messages: list[WorkerMessage] = []
        while True:
            try:
                messages.append(self._received_messages.get_nowait())
            except queue.Empty:
                return messages

    def _release_finished_workers(self, messages: list[WorkerMessage]) -> None:
        """Marca libres a los workers que terminaron su job."""
        finished_worker_ids = {m.worker_id for m in messages if m.ends_the_job_run}
        for worker in self._workers:
            if worker.worker_id in finished_worker_ids:
                worker.assigned_job_id = None

    def _replace_crashed_workers(self) -> list[WorkerMessage]:
        """Sustituye los workers muertos y falla el job que tenían asignado.

        Antes de decidir, recoge lo que el worker llegó a enviar: si terminó su
        job y luego salió, ya está libre y no cuenta como caído.
        """
        late_messages: list[WorkerMessage] = []
        for index, worker in enumerate(self._workers):
            if worker.process.is_alive():
                continue
            logger.error(
                "Worker %s exited with code %s",
                worker.worker_id,
                worker.process.exitcode,
            )
            worker.stop_receivers()
            received = self._take_received_messages()
            self._release_finished_workers(received)
            late_messages.extend(received)
            if worker.assigned_job_id is not None:
                late_messages.append(_crash_message(worker, worker.assigned_job_id))
            self._workers[index] = self._start_worker()
        return late_messages


def _crash_message(worker: WorkerHandle, job_id: JobId) -> WorkerMessage:
    """JobFailed que el pool publica en nombre de un worker caído (UC-03 A4)."""
    return WorkerMessage(
        worker_id=worker.worker_id,
        job_id=job_id,
        sequence_number=POOL_SEQUENCE_NUMBER,
        job_event=JobFailed(
            failure_reason=FailureReason.WORKER_CRASHED,
            failure_message=(
                f"Worker {worker.worker_id} stopped unexpectedly "
                f"with exit code {worker.process.exitcode}"
            ),
        ),
    )
