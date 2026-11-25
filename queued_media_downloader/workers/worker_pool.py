"""Contrato del conjunto de workers que ejecuta los jobs."""

from typing import Protocol

from queued_media_downloader.jobs import Job, JobId
from queued_media_downloader.workers.worker_message import WorkerMessage


class NoIdleWorkerError(Exception):
    """Se envió un job sin ningún worker libre."""

    def __init__(self) -> None:
        """Compone el mensaje para los logs."""
        super().__init__("No idle worker is available")


class WorkerPool(Protocol):
    """Ejecuta jobs en workers y devuelve lo que publican."""

    def submit(self, job: Job) -> None:
        """Envía el job a un worker libre.

        Raises:
            NoIdleWorkerError: Si todos los workers están ocupados.
        """
        ...

    def collect_events(self, timeout_seconds: float) -> list[WorkerMessage]:
        """Devuelve los mensajes recibidos; espera hasta timeout_seconds al primero.

        Si un worker murió con un job asignado, termina sus descendientes,
        incluye un JobFailed con WORKER_CRASHED para ese job y arranca un worker
        de reemplazo.
        """
        ...

    def request_cancellation(self, job_id: JobId) -> None:
        """Pide al worker que ejecuta job_id que lo detenga (UC-05, paso 5).

        Es cooperativa: el worker la ve en el siguiente job event que publica y
        termina con JobCancelled. Si el job ya terminó, no tiene efecto.
        """
        ...

    def terminate_worker_running(self, job_id: JobId) -> bool:
        """Termina el árbol de procesos del worker que ejecuta job_id y lo sustituye.

        No publica nada en nombre del job: quien lo pide decide su estado.

        Returns:
            True si había un worker ejecutando job_id.
        """
        ...

    def count_idle_workers(self) -> int:
        """Número de workers sin job asignado."""
        ...

    def shut_down(self) -> None:
        """Detiene todos los workers."""
        ...
