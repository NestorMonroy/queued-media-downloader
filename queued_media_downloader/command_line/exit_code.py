"""Códigos de salida de la línea de comandos (SUP-F02)."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Código con el que termina el proceso de la línea de comandos."""

    SUCCESS = 0
    JOBS_FAILED = 1
    USAGE_ERROR = 2
    # Convención de los intérpretes de comandos: 128 + SIGINT (UC-05 A6).
    INTERRUPTED = 130
