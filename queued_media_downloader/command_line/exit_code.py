"""Códigos de salida de la línea de comandos (SUP-F02)."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Código con el que termina el proceso de la línea de comandos."""

    SUCCESS = 0
    USAGE_ERROR = 2
