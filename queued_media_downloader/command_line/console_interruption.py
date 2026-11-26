"""Ctrl+C durante run (UC-05 A6): el primero detiene la cola, el segundo ya.

Ctrl+C no cancela ningún job (ADR-0029): los jobs en curso conservan su estado
y sus parciales, y continúan en el siguiente run (UC-06).
"""

import signal
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from types import FrameType


class InterruptionRequest:
    """stop_requested de RunQueue, que activa el primer Ctrl+C.

    El segundo Ctrl+C lanza KeyboardInterrupt, como sin este manejador: run
    termina entonces el árbol de cada worker sin esperar. Los siguientes se
    ignoran: un KeyboardInterrupt a mitad de ese apagado dejaría workers sin
    terminar y una traza en la consola.
    """

    def __init__(self) -> None:
        """Empieza sin interrupción pedida."""
        self._requested = False
        self._stopping_at_once = False
        self._told_to_wait = False

    def __call__(self) -> bool:
        """Indica si el User pulsó Ctrl+C."""
        return self._requested

    def handle_signal(self, signal_number: int, frame: FrameType | None) -> None:
        """Manejador de SIGINT."""
        del signal_number, frame
        if self._stopping_at_once:
            if not self._told_to_wait:
                self._told_to_wait = True
                print("Already stopping; please wait", file=sys.stdout, flush=True)
            return
        if self._requested:
            self._stopping_at_once = True
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
        # Tras un Ctrl+C el programa está terminando: los siguientes se ignoran
        # hasta que salga, para que ninguno corte el cierre con una traza.
        if interruption_request():
            signal.signal(signal.SIGINT, signal.SIG_IGN)
        else:
            signal.signal(signal.SIGINT, previous_handler)
