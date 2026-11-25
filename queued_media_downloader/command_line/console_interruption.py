"""Ctrl+C durante run (UC-05 A6): el primero detiene la cola, el segundo ya."""

import signal
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from types import FrameType


class InterruptionRequest:
    """stop_requested de RunQueue, que activa el primer Ctrl+C.

    El segundo Ctrl+C lanza KeyboardInterrupt, como sin este manejador: run
    termina entonces el árbol de cada worker sin esperar.
    """

    def __init__(self) -> None:
        """Empieza sin interrupción pedida."""
        self._requested = False

    def __call__(self) -> bool:
        """Indica si el User pulsó Ctrl+C."""
        return self._requested

    def handle_signal(self, signal_number: int, frame: FrameType | None) -> None:
        """Manejador de SIGINT."""
        del signal_number, frame
        if self._requested:
            raise KeyboardInterrupt
        self._requested = True
        print(
            "Interrupting: stopping the running jobs; "
            "press Ctrl+C again to stop at once",
            file=sys.stdout,
            flush=True,
        )


@contextmanager
def handling_interruptions() -> Iterator[InterruptionRequest]:
    """Instala el manejador de Ctrl+C mientras se ejecuta la cola."""
    interruption_request = InterruptionRequest()
    previous_handler = signal.signal(signal.SIGINT, interruption_request.handle_signal)
    try:
        yield interruption_request
    finally:
        signal.signal(signal.SIGINT, previous_handler)
