"""Cancelación cooperativa dentro del worker (UC-05, paso 5).

El hilo principal del worker está dentro de yt-dlp mientras ejecuta un job, así
que no puede leer instrucciones. Un hilo aparte escucha la cola de
cancelaciones y anota los jobs cancelados; el hilo principal lo comprueba cada
vez que el job publica un job event que no es final.
"""

import threading
from typing import Protocol

from queued_media_downloader.jobs import JobId
from queued_media_downloader.workers.worker_instructions import CancelJob


class CancellationQueue(Protocol):
    """Lo que el worker necesita de su cola de cancelaciones."""

    def get(self) -> CancelJob:
        """Espera y devuelve la siguiente cancelación."""
        ...


class JobCancellationListener:
    """Anota en segundo plano los jobs cuya cancelación pide el proceso principal.

    Guarda los ids aunque el job aún no haya empezado: la cancelación puede
    llegar antes que su RunJob, porque viajan por colas distintas.
    """

    def __init__(self, cancellation_queue: CancellationQueue) -> None:
        """Escucha cancellation_queue en un hilo daemon, que muere con el worker."""
        self._cancellation_queue = cancellation_queue
        self._cancelled_job_ids: set[JobId] = set()
        self._lock = threading.Lock()
        threading.Thread(
            target=self._listen, name="job-cancellation-listener", daemon=True
        ).start()

    def is_cancelled(self, job_id: JobId) -> bool:
        """Indica si el proceso principal pidió cancelar job_id."""
        with self._lock:
            return job_id in self._cancelled_job_ids

    def _listen(self) -> None:
        while True:
            cancel_job = self._cancellation_queue.get()
            with self._lock:
                self._cancelled_job_ids.add(cancel_job.job_id)
