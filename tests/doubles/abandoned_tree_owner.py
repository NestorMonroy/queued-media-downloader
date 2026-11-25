"""Proceso dueño de un árbol registrado, que la prueba termina a la fuerza.

Uso: python -m tests.doubles.abandoned_tree_owner DIRECTORIO
"""

import sys
import time
from pathlib import Path

from tests.doubles.process_tree import start_tree


def main() -> None:
    """Crea el terminador de Windows, arranca un árbol y espera."""
    if sys.platform == "win32":
        from queued_media_downloader.workers.windows_process_tree_terminator import (
            WindowsProcessTreeTerminator,
        )

        terminator = WindowsProcessTreeTerminator()
        start_tree(Path(sys.argv[1]), terminator.register_root_process)
        while True:
            time.sleep(1)


if __name__ == "__main__":
    main()
