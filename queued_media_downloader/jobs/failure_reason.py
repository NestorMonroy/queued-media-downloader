"""Clasificación de dominio de los fallos de un job."""

from enum import StrEnum


class FailureReason(StrEnum):
    """Motivo por el que falló un job, independiente de las excepciones de yt-dlp."""

    NETWORK = "NETWORK"
    EXTRACTOR_OUTDATED = "EXTRACTOR_OUTDATED"
    GEO_RESTRICTED = "GEO_RESTRICTED"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED_URL = "UNSUPPORTED_URL"
    POSTPROCESSING = "POSTPROCESSING"
    FILESYSTEM = "FILESYSTEM"
    WORKER_CRASHED = "WORKER_CRASHED"
    UNKNOWN = "UNKNOWN"
