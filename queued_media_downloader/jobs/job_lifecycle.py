"""Transiciones permitidas entre los estados de un job (diseño, Parte 1, §6)."""

from queued_media_downloader.jobs.job_status import JobStatus

ALLOWED_TRANSITIONS: frozenset[tuple[JobStatus, JobStatus]] = frozenset(
    {
        (JobStatus.PENDING, JobStatus.RUNNING),
        (JobStatus.PENDING, JobStatus.CANCELLED),
        (JobStatus.RUNNING, JobStatus.COMPLETED),
        (JobStatus.RUNNING, JobStatus.FAILED),
        (JobStatus.RUNNING, JobStatus.CANCELLATION_REQUESTED),
        # Recuperación al arrancar y URL que resulta ser un solo contenido.
        (JobStatus.RUNNING, JobStatus.PENDING),
        # La URL resulta ser un contenido que ya tiene una descarga (UC-03 A1).
        (JobStatus.RUNNING, JobStatus.SKIPPED),
        (JobStatus.CANCELLATION_REQUESTED, JobStatus.CANCELLED),
        # El job terminó antes de ver la petición de cancelación.
        (JobStatus.CANCELLATION_REQUESTED, JobStatus.COMPLETED),
        (JobStatus.FAILED, JobStatus.PENDING),
        (JobStatus.CANCELLED, JobStatus.PENDING),
    }
)


class InvalidJobTransitionError(Exception):
    """Se intentó una transición que el ciclo de vida de un job no permite."""

    def __init__(self, current_status: JobStatus, target_status: JobStatus) -> None:
        """Guarda ambos estados y compone el mensaje para los logs."""
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Job cannot move from {current_status.value} to {target_status.value}"
        )


def is_transition_allowed(current_status: JobStatus, target_status: JobStatus) -> bool:
    """Indica si un job puede pasar de current_status a target_status."""
    return (current_status, target_status) in ALLOWED_TRANSITIONS


def ensure_transition_allowed(
    current_status: JobStatus, target_status: JobStatus
) -> None:
    """Lanza InvalidJobTransitionError si la transición no está permitida."""
    if not is_transition_allowed(current_status, target_status):
        raise InvalidJobTransitionError(current_status, target_status)
