"""Aplica a los jobs guardados los job events que publican los workers.

Solo el proceso de run cambia el estado de los jobs (diseño, Parte 2, §2.4);
este módulo es el único sitio donde un job event se convierte en un cambio.
"""

import logging

from queued_media_downloader.job_storage import DuplicateOutputPathError, JobStore
from queued_media_downloader.jobs import (
    FailureReason,
    FormatSelected,
    Job,
    JobCancelled,
    JobCompleted,
    JobFailed,
    JobKind,
    JobStatus,
    MediaKey,
    PlaylistEntriesFound,
    PlaylistEntry,
    SingleMediaFound,
)
from queued_media_downloader.workers import WorkerMessage

logger = logging.getLogger(__name__)

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

        Un lote de playlist crea los jobs hijos y da a la expansión el título
        de la playlist, si aún no tenía uno.

        Returns:
            El job tal como quedó guardado; None para un lote de playlist o si
            el job event no cambia el job del mensaje.
        """
        job_event = message.job_event
        if isinstance(job_event, PlaylistEntriesFound):
            expansion = self._job_store.get(message.job_id)
            # Una expansión que se está cancelando ya no crea hijos (UC-05 A4).
            if expansion.status is JobStatus.RUNNING:
                if job_event.playlist_title and expansion.title is None:
                    self._job_store.update(
                        expansion.record_playlist_title(job_event.playlist_title)
                    )
                self._create_playlist_children(expansion, job_event)
            return None
        if not isinstance(job_event, PERSISTENT_JOB_EVENT_TYPES):
            return None
        stored_job = self._job_store.get(message.job_id)
        if stored_job.is_finished():
            # Lo que un worker envió antes de que se terminara su árbol
            # (UC-05 A2): el job ya tiene su estado definitivo.
            logger.info(
                "Ignoring %s for job %s, already %s",
                type(job_event).__name__,
                message.job_id,
                stored_job.status.value,
            )
            return None
        updated_job = self._job_after(stored_job, job_event)
        try:
            self._job_store.update(updated_job)
        except DuplicateOutputPathError as duplicate_output:
            # Otro contenido con el mismo nombre final (plantilla sin %(id)s o
            # título recortado): el archivo es del otro job, no de este (R-14).
            updated_job = stored_job.fail(
                FailureReason.FILESYSTEM,
                f"{duplicate_output}; use an output template that keeps %(id)s",
            )
            self._job_store.update(updated_job)
        return updated_job

    def _create_playlist_children(
        self, expansion: Job, playlist_batch: PlaylistEntriesFound
    ) -> None:
        """Guarda de una vez un job hijo por entrada del lote (UC-04, paso 4).

        Una entrada repetida dentro del mismo lote cuenta como duplicada (A2),
        aunque su primera aparición aún no esté guardada.
        """
        claimed_media_keys: set[MediaKey] = set()
        children: list[Job] = []
        for playlist_entry in playlist_batch.playlist_entries:
            child = Job.new_playlist_child(
                expansion,
                playlist_batch,
                playlist_entry,
                is_duplicate=self._is_duplicate(
                    playlist_entry, claimed_media_keys, expansion
                ),
            )
            if child.media_key is not None and child.status is JobStatus.PENDING:
                claimed_media_keys.add(child.media_key)
            children.append(child)
        self._job_store.create_many(children)

    def _is_duplicate(
        self,
        playlist_entry: PlaylistEntry,
        claimed_media_keys: set[MediaKey],
        expansion: Job,
    ) -> bool:
        """Indica si el contenido de la entrada ya tiene una descarga (A2)."""
        media_key = playlist_entry.media_key
        if media_key is None:
            return False
        return media_key in claimed_media_keys or self._job_store.has_active_download(
            media_key, audio_only=expansion.download_options.audio_only
        )

    @staticmethod
    def _completed(job: Job, output_path: str | None) -> Job:
        """El job completado o, si el evento rompe el contrato, fallido.

        Un worker nunca debería publicarlo (YtDlpMediaSource lo comprueba
        antes); si pasara, el job no puede quedar COMPLETED sin su archivo ni
        detener la cola.
        """
        try:
            return job.complete(output_path)
        except ValueError as contract_error:
            logger.error("Job %s: %s", job.job_id, contract_error)
            if job.kind is JobKind.DOWNLOAD:
                return job.fail(
                    FailureReason.FILESYSTEM,
                    "The download finished without an output file",
                )
            return job.fail(FailureReason.UNKNOWN, str(contract_error))

    def _job_after(self, job: Job, job_event: PersistentJobEvent) -> Job:
        """Devuelve el job tal como queda tras job_event.

        Mientras se cancela, cualquier final que no sea JobCompleted confirma la
        cancelación: un fallo o un contenido encontrado ya no interesan al User,
        y JobCompleted gana porque el archivo ya está terminado (UC-05 A3).
        """
        if job.status is JobStatus.CANCELLATION_REQUESTED and isinstance(
            job_event, SingleMediaFound | JobFailed | JobCancelled
        ):
            return job.confirm_cancellation()
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
                return self._completed(job, output_path)
            case JobFailed(failure_reason=failure_reason, failure_message=message):
                return job.fail(failure_reason, message)
            case JobCancelled():
                return job.confirm_cancellation()
