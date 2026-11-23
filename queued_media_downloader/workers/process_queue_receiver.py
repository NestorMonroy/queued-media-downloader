"""Hilo que recibe lo que un worker envía por su cola de multiprocessing.

Cada worker escribe en sus propias colas: el bloqueo de escritura de una cola de
multiprocessing se comparte entre los procesos que escriben en ella, y un
worker que muere mientras escribe (caída o terminación forzada) dejaría
bloqueados a los demás.
"""

import queue
import threading
from collections.abc import Callable
from typing import Any

# Cada cuánto el receptor comprueba si debe terminar.
RECEIVE_TIMEOUT_SECONDS = 0.1
# Espera máxima al receptor de un worker caído, por si su cola quedó dañada.
STOP_TIMEOUT_SECONDS = 2.0


class ProcessQueueReceiver:
    """Entrega a deliver cada elemento que llega por la cola de un worker.

    Nunca escribe en la cola (QueueListener sí, para detenerse), así que
    detenerlo no se bloquea aunque el worker muriera escribiendo en ella.
    """

    def __init__(
        self, source_queue: Any, deliver: Callable[[Any], None], name: str
    ) -> None:
        """Empieza a recibir en un hilo propio."""
        self._source_queue = source_queue
        self._deliver = deliver
        self._stopping = threading.Event()
        self._thread = threading.Thread(target=self._receive, name=name, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Entrega lo que quede en la cola y termina."""
        self._stopping.set()
        self._thread.join(STOP_TIMEOUT_SECONDS)

    def _receive(self) -> None:
        """Entrega cada elemento; acaba cuando debe parar y la cola está vacía."""
        while True:
            try:
                element = self._source_queue.get(timeout=RECEIVE_TIMEOUT_SECONDS)
            except queue.Empty:
                if self._stopping.is_set():
                    return
                continue
            except (EOFError, OSError):
                return
            self._deliver(element)
