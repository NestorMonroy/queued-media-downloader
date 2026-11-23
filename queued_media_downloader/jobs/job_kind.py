"""Tipos de job."""

from enum import StrEnum


class JobKind(StrEnum):
    """Qué hace un job: expandir una URL o descargar un contenido (ADR-0009)."""

    EXPANSION = "EXPANSION"
    DOWNLOAD = "DOWNLOAD"
