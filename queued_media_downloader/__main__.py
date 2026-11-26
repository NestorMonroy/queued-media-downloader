"""Punto de entrada del programa, como comando o con ``python -m``."""

import io
import sys

from queued_media_downloader.command_line import main as run_command_line


def main() -> None:
    """Ejecuta la línea de comandos y termina el proceso con su código de salida."""
    replace_unencodable_output()
    sys.exit(run_command_line())


def replace_unencodable_output() -> None:
    """La salida nunca falla por un carácter que su codificación no tiene.

    En Windows, cuando la salida va a un archivo o a una tubería, Python usa la
    codificación local (cp1252), sin emojis ni muchos caracteres de los títulos:
    un print fallaba a mitad de list o de run (T42-D4). Esos caracteres se
    escriben como "?"; en una consola, Windows recibe el texto completo.
    """
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="replace")


# Los workers se crean con spawn: cada uno importa este módulo, y el guard evita
# que vuelvan a ejecutar la línea de comandos (ADR-0004).
if __name__ == "__main__":
    main()
