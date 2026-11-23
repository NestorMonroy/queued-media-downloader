"""Punto de entrada del programa, como comando o con ``python -m``."""

import sys

from queued_media_downloader.command_line import main as run_command_line


def main() -> None:
    """Ejecuta la línea de comandos y termina el proceso con su código de salida."""
    sys.exit(run_command_line())


# Los workers se crean con spawn: cada uno importa este módulo, y el guard evita
# que vuelvan a ejecutar la línea de comandos (ADR-0004).
if __name__ == "__main__":
    main()
