"""Bucle que ejecuta un worker en su propio proceso (diseño, Parte 2, §3.2)."""

import logging
from collections.abc import Callable
from typing import Any, Protocol

from queued_media_downloader.jobs import (
    FailureReason,
    Job,
    JobCancelled,
    JobEvent,
    JobFailed,
    JobId,
    JobKind,
    JobStarted,
)
from queued_media_downloader.media_extraction import (
    JobCancelledError,
    MediaSource,
    Publish,
)
from queued_media_downloader.workers.job_cancellation import (
    CancellationQueue,
    JobCancellationListener,
)
from queued_media_downloader.workers.process_tree_terminator import (
    become_process_tree_root,
)
from queued_media_downloader.workers.worker_instructions import (
    RunJob,
    WorkerInstruction,
)
from queued_media_downloader.workers.worker_logging import configure_worker_logging
from queued_media_downloader.workers.worker_message import (
    FINAL_JOB_EVENT_TYPES,
    WorkerMessage,
)

logger = logging.getLogger(__name__)


class InstructionQueue(Protocol):
    """Lo que el worker necesita de su cola de instrucciones."""

    def get(self) -> WorkerInstruction:
        """Espera y devuelve la siguiente instrucción."""
        ...


class MessageQueue(Protocol):
    """Lo que el worker necesita de la cola compartida de mensajes."""

    def put(self, message: WorkerMessage) -> None:
        """Envía un mensaje al proceso principal."""
        ...


class WorkerMessageSender:
    """Envuelve cada job event en un WorkerMessage numerado y lo envía."""

    def __init__(self, worker_id: int, message_queue: MessageQueue) -> None:
        """Numera los mensajes de este worker desde 1."""
        self._worker_id = worker_id
        self._message_queue = message_queue
        self._sequence_number = 0

    def publisher_for(
        self, job_id: JobId, is_cancelled: Callable[[JobId], bool]
    ) -> Publish:
        """Función publish que la MediaSource usa para un job.

        Si el job tiene pedida su cancelación, lanza JobCancelledError en lugar
        de publicar un job event que no es final: así la cancelación se ve en el
        siguiente avance de yt-dlp. Un evento final se publica siempre, para
        que un job ya terminado no pase por cancelado (UC-05 A3).
        """

        def publish(job_event: JobEvent) -> None:
            if not isinstance(job_event, FINAL_JOB_EVENT_TYPES) and is_cancelled(
                job_id
            ):
                raise JobCancelledError
            self.send(job_id, job_event)

        return publish

    def send(self, job_id: JobId, job_event: JobEvent) -> None:
        """Envía job_event como mensaje del job job_id."""
        self._sequence_number += 1
        self._message_queue.put(
            WorkerMessage(
                worker_id=self._worker_id,
                job_id=job_id,
                sequence_number=self._sequence_number,
                job_event=job_event,
            )
        )


def worker_loop(
    worker_id: int,
    media_source_factory: Callable[[], MediaSource],
    instruction_queue: InstructionQueue,
    message_queue: MessageQueue,
    log_queue: Any,
    cancellation_queue: CancellationQueue,
) -> None:
    """Ejecuta los jobs que llegan por instruction_queue hasta recibir ShutDown.

    La MediaSource se crea una sola vez, ya dentro del proceso del worker. Los
    registros de logging del worker viajan por log_queue al proceso principal;
    las cancelaciones llegan por cancellation_queue a un hilo aparte.
    """
    # Antes de cualquier job: los procesos que lance yt-dlp quedan en su árbol.
    become_process_tree_root()
    configure_worker_logging(log_queue)
    cancellation_listener = JobCancellationListener(cancellation_queue)
    media_source = media_source_factory()
    message_sender = WorkerMessageSender(worker_id, message_queue)
    while isinstance(instruction := instruction_queue.get(), RunJob):
        job = instruction.job
        if job.job_id is None:
            message = "Only stored jobs can be run"
            raise ValueError(message)
        publish = message_sender.publisher_for(
            job.job_id, cancellation_listener.is_cancelled
        )
        message_sender.send(job.job_id, JobStarted())
        _run_job(media_source, job, publish, message_sender)


def _run_job(
    media_source: MediaSource,
    job: Job,
    publish: Publish,
    message_sender: WorkerMessageSender,
) -> None:
    """Expande o descarga el job; un error inesperado falla el job, no el worker."""
    assert job.job_id is not None
    try:
        if job.kind is JobKind.EXPANSION:
            media_source.expand(job, publish)
        else:
            media_source.download(job, publish)
    except JobCancelledError:
        message_sender.send(job.job_id, JobCancelled())
    except Exception as unexpected_error:
        logger.exception("Job %s failed unexpectedly", job.job_id)
        publish(
            JobFailed(
                failure_reason=FailureReason.UNKNOWN,
                failure_message=str(unexpected_error),
            )
        )
