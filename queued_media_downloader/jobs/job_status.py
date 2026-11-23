"""Estados del ciclo de vida de un job."""

from enum import StrEnum


class JobStatus(StrEnum):
    """Estado de un job; las transiciones permitidas están en job_lifecycle."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"
