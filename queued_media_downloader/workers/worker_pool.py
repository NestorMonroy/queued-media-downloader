"""Contrato del conjunto de workers que ejecuta los jobs."""

from typing import Protocol

from queued_media_downloader.jobs import Job
from queued_media_downloader.workers.worker_message import WorkerMessage


class NoIdleWorkerError(Exception):
    """Se envió un job sin ningún worker libre."""

    def __init__(self) -> None:
        """Compone el mensaje para los logs."""
        super().__init__("No idle worker is available")


class WorkerPool(Protocol):
    """Ejecuta jobs en workers y devuelve lo que publican.

    La cancelación (request_cancellation, terminate_worker_running) se añade
    con el caso de uso que la necesita.
    """

    def submit(self, job: Job) -> None:
        """Envía el job a un worker libre.

        Raises:
            NoIdleWorkerError: Si todos los workers están ocupados.
        """
        ...

    def collect_events(self, timeout_seconds: float) -> list[WorkerMessage]:
        """Devuelve los mensajes recibidos; espera hasta timeout_seconds al primero.

        Si un worker murió con un job asignado, incluye un JobFailed con
        WORKER_CRASHED para ese job y arranca un worker de reemplazo.
        """
        ...

    def count_idle_workers(self) -> int:
        """Número de workers sin job asignado."""
        ...

    def shut_down(self) -> None:
        """Detiene todos los workers."""
        ...
