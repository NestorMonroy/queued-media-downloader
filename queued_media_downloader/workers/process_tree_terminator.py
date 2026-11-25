"""Contrato para terminar el árbol de procesos de un worker (ADR-0013, ADR-0029).

Un worker ejecuta yt-dlp, que lanza ffmpeg, ffprobe y deno con subprocess.Popen
sin creationflags. Terminar solo el worker deja vivos a esos descendientes
(ADR-0029, hallazgo 1): el pool termina siempre el árbol entero.
"""

import os
import sys
from typing import Protocol


class ProcessTreeTerminationError(Exception):
    """No se pudo registrar o terminar el árbol de procesos de un worker."""


class ProcessTreeTerminator(Protocol):
    """Termina un proceso raíz junto con todos los procesos que este cree.

    Un terminador sirve a un solo worker durante toda su vida.
    """

    def register_root_process(self, process_id: int) -> None:
        """Registra el proceso cuyo árbol completo se terminará.

        Debe llamarse nada más arrancar el worker y antes de enviarle ningún
        job: solo los procesos que cree después quedan dentro de su árbol.

        Raises:
            ProcessTreeTerminationError: Si el proceso no se puede registrar.
        """
        ...

    def terminate_tree(self) -> None:
        """Termina el proceso raíz y todos sus descendientes.

        Termina también los descendientes de una raíz que ya murió. Puede
        llamarse varias veces; no hace nada tras release().
        """
        ...

    def release(self) -> None:
        """Libera los recursos del terminador al sustituir o apagar el worker.

        Puede terminar lo que quede vivo del árbol. Puede llamarse varias veces.
        """
        ...


def become_process_tree_root() -> None:
    """Prepara el proceso actual (el worker) como raíz de su árbol.

    El worker la llama al arrancar, antes de leer su primera instrucción. En
    POSIX crea su propio grupo de procesos, que heredan los procesos que lance:
    un proceso padre no puede cambiar el grupo de un hijo que ya ejecutó exec.
    En Windows no hace nada: el proceso principal asigna el worker a su Job
    Object (WindowsProcessTreeTerminator).
    """
    if sys.platform != "win32":
        os.setpgid(0, 0)
