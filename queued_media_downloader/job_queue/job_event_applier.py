"""Aplica a los jobs guardados los job events que publican los workers.

Solo el proceso de run cambia el estado de los jobs (diseño, Parte 2, §2.4);
este módulo es el único sitio donde un job event se convierte en un cambio.
"""

from queued_media_downloader.job_storage import JobStore
from queued_media_downloader.jobs import (
    FormatSelected,
    Job,
    JobCancelled,
    JobCompleted,
    JobFailed,
    SingleMediaFound,
)
from queued_media_downloader.workers import WorkerMessage

# Job events que solo informan del avance: no se persisten (diseño, Parte 1, §5).
# JobStarted tampoco cambia nada: el job pasó a RUNNING al enviarse.
PersistentJobEvent = (
    SingleMediaFound | FormatSelected | JobCompleted | JobFailed | JobCancelled
)
PERSISTENT_JOB_EVENT_TYPES = (
    SingleMediaFound,
    FormatSelected,
    JobCompleted,
    JobFailed,
    JobCancelled,
)


class JobEventApplier:
    """Actualiza en el JobStore el job al que se refiere cada mensaje."""

    def __init__(self, job_store: JobStore) -> None:
        """Usa job_store para leer y guardar los jobs."""
        self._job_store = job_store

    def apply(self, message: WorkerMessage) -> Job | None:
        """Aplica el job event del mensaje, si cambia algo del job.

        Returns:
            El job tal como quedó guardado; None si el job event solo informa
            del avance y no cambia el job.
        """
        job_event = message.job_event
        if not isinstance(job_event, PERSISTENT_JOB_EVENT_TYPES):
            return None
        updated_job = self._job_after(self._job_store.get(message.job_id), job_event)
        self._job_store.update(updated_job)
        return updated_job

    def _job_after(self, job: Job, job_event: PersistentJobEvent) -> Job:
        """Devuelve el job tal como queda tras job_event."""
        match job_event:
            case SingleMediaFound(media_key=media_key, title=title):
                if self._job_store.has_active_download(
                    media_key, audio_only=job.download_options.audio_only
                ):
                    return job.skip_as_duplicate(media_key, title)
                return job.found_single_media(media_key, title)
            case FormatSelected(selected_format_id=selected_format_id):
                return job.record_selected_format(selected_format_id)
            case JobCompleted(output_path=output_path):
                return job.complete(output_path)
            case JobFailed(failure_reason=failure_reason, failure_message=message):
                return job.fail(failure_reason, message)
            case JobCancelled():
                return job.confirm_cancellation()
