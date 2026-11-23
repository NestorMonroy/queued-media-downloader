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
from multiprocessing.context import SpawnProcess
from multiprocessing.queues import Queue

from queued_media_downloader.jobs import FailureReason, Job, JobFailed, JobId
from queued_media_downloader.media_extraction import MediaSource
from queued_media_downloader.workers.worker_instructions import (
    RunJob,
    ShutDown,
    WorkerInstruction,
)
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
    assigned_job_id: JobId | None = None


class ProcessWorkerPool:
    """Ejecuta cada job en uno de worker_count procesos.

    Cada worker tiene su cola de instrucciones; todos comparten la cola de
    mensajes hacia el proceso principal (diseño, Parte 2, §3.1).
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
        self._message_queue: Queue[WorkerMessage] = self._context.Queue()
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
        for message in messages:
            if message.ends_the_job_run:
                self._release_worker(message.worker_id)
        # Se comprueba después de vaciar la cola: un worker que terminó su job y
        # luego salió ya está libre y no cuenta como caído.
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
        self._workers = []

    def _start_worker(self) -> WorkerHandle:
        """Arranca un proceso worker con su cola de instrucciones."""
        worker_id = next(self._worker_ids)
        instruction_queue: Queue[WorkerInstruction] = self._context.Queue()
        process = self._context.Process(
            target=worker_loop,
            args=(
                worker_id,
                self._media_source_factory,
                instruction_queue,
                self._message_queue,
            ),
            name=f"worker-{worker_id}",
            daemon=True,
        )
        process.start()
        return WorkerHandle(worker_id, process, instruction_queue)

    def _receive_messages(self, timeout_seconds: float) -> list[WorkerMessage]:
        """Espera el primer mensaje hasta timeout_seconds y toma los ya llegados."""
        try:
            messages = [self._message_queue.get(timeout=timeout_seconds)]
        except queue.Empty:
            return []
        while True:
            try:
                messages.append(self._message_queue.get_nowait())
            except queue.Empty:
                return messages

    def _release_worker(self, worker_id: int) -> None:
        """Marca libre al worker que terminó su job."""
        for worker in self._workers:
            if worker.worker_id == worker_id:
                worker.assigned_job_id = None

    def _replace_crashed_workers(self) -> list[WorkerMessage]:
        """Sustituye los workers muertos y falla el job que tenían asignado."""
        crash_messages: list[WorkerMessage] = []
        for index, worker in enumerate(self._workers):
            if worker.process.is_alive():
                continue
            logger.error(
                "Worker %s exited with code %s",
                worker.worker_id,
                worker.process.exitcode,
            )
            if worker.assigned_job_id is not None:
                crash_messages.append(_crash_message(worker, worker.assigned_job_id))
            self._workers[index] = self._start_worker()
        return crash_messages


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
