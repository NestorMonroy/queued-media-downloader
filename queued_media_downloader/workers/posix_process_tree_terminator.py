"""Terminación del árbol de un worker con un grupo de procesos (POSIX).

Sirve para ejecutar el pool con procesos reales en cualquier sistema; el
producto es solo para Windows (ADR-0004, ADR-0029). Diferencias con Windows:
- El árbol no muere si muere el proceso principal: un grupo de procesos no
  tiene nada equivalente a JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE.
- Un descendiente puede salir del grupo con setpgid o setsid; ffmpeg y deno no
  lo hacen.
"""

import contextlib
import os
import signal
import sys


class PosixProcessTreeTerminator:
    """Envía SIGKILL al grupo de procesos que encabeza el worker."""

    def __init__(self) -> None:
        """Empieza sin raíz registrada."""
        self._root_process_id: int | None = None
        self._root_handle: int | None = None

    def register_root_process(self, process_id: int) -> None:
        """Registra el worker, que crea su grupo con become_process_tree_root.

        Abre un pidfd del worker, donde existe, para poder terminarlo sin
        confundirlo con otro proceso que reciba su PID más adelante.
        """
        self._root_process_id = process_id
        if hasattr(os, "pidfd_open"):
            with contextlib.suppress(ProcessLookupError):
                self._root_handle = os.pidfd_open(process_id)

    def terminate_tree(self) -> None:
        """SIGKILL al grupo; si el worker aún no lo creó, al worker solo.

        Mientras el grupo tenga miembros, su id no se reutiliza como PID, así
        que killpg no puede alcanzar a otro grupo.
        """
        if self._root_process_id is None or sys.platform == "win32":
            return
        try:
            os.killpg(self._root_process_id, signal.SIGKILL)
        except ProcessLookupError:
            # Sin grupo: el worker aún no ejecutó become_process_tree_root, así
            # que no lanzó ningún proceso. Basta con terminar el worker.
            self._kill_root()

    def release(self) -> None:
        """Olvida el worker y cierra su pidfd."""
        if self._root_handle is not None:
            os.close(self._root_handle)
        self._root_handle = None
        self._root_process_id = None

    def _kill_root(self) -> None:
        if sys.platform == "win32":
            return
        with contextlib.suppress(ProcessLookupError):
            if self._root_handle is not None:
                signal.pidfd_send_signal(self._root_handle, signal.SIGKILL)
            elif self._root_process_id is not None:
                os.kill(self._root_process_id, signal.SIGKILL)
