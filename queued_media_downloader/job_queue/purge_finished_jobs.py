"""Caso de uso UC-10: borrar de la cola los jobs terminados.

Los archivos descargados no se tocan. Sí se borran la carpeta de parciales de
cada job purgado (los ids no se reutilizan, T44, así que nadie más la borraría)
y las reclamaciones de nombres finales de los jobs que ya no existen (R-14,
ADR-0030): el archivo sigue protegido, porque un job nuevo no lo toma como
suyo si no lo escribió él.
"""

from collections.abc import Collection, Iterator
from dataclasses import dataclass

from queued_media_downloader.job_storage import JobStore
from queued_media_downloader.jobs import Job, JobId, JobKind, JobStatus
from queued_media_downloader.media_extraction import (
    OutputClaims,
    remove_partial_directory,
)

PURGEABLE_STATUSES = frozenset({JobStatus.COMPLETED, JobStatus.CANCELLED})


@dataclass(frozen=True, slots=True)
class PurgeResult:
    """Cuántos jobs se borraron y qué playlists se conservaron."""

    deleted_job_count: int
    # Playlists terminadas con alguna entrada que no se puede purgar.
    kept_playlists: list[Job]


class PurgeFinishedJobs:
    """Borra los jobs COMPLETED y/o CANCELLED, y las playlists ya sin trabajo."""

    def __init__(self, job_store: JobStore, output_claims: OutputClaims) -> None:
        """Lee y borra en job_store; suelta las reclamaciones en output_claims."""
        self._job_store = job_store
        self._output_claims = output_claims

    def execute(self, statuses: Collection[JobStatus]) -> PurgeResult:
        """Borra los jobs en esos estados (COMPLETED, CANCELLED o ambos).

        Una playlist arrastra a sus entradas (ON DELETE CASCADE), así que solo
        se borra si todas sus entradas se pueden borrar también; las SKIPPED,
        que solo marcan duplicados de esa playlist, se van con ella.

        Raises:
            ValueError: Si se pide purgar un estado que no está terminado.
        """
        if not set(statuses) <= PURGEABLE_STATUSES:
            message = f"Only {sorted(PURGEABLE_STATUSES)} jobs can be purged"
            raise ValueError(message)
        removable_statuses = {*statuses, JobStatus.SKIPPED}
        deleted: dict[JobId, Job] = {}
        kept_playlists: list[Job] = []
        for job in self._job_store.get_with_status(statuses):
            descendants = list(self._descendants(job))
            if any(d.status not in removable_statuses for d in descendants):
                kept_playlists.append(job)
                continue
            for removed in (job, *descendants):
                if removed.job_id is not None:
                    deleted[removed.job_id] = removed
        # Primero la base de datos: si está ocupada (JobStoreLockedError), no
        # se toca nada. Después, los parciales de los jobs borrados y las
        # reclamaciones de jobs que ya no existen, incluidas las que dejó una
        # terminación forzada o un purge anterior interrumpido.
        self._job_store.delete(list(deleted))
        for removed in deleted.values():
            remove_partial_directory(removed.partial_directory())
        remaining_job_ids = {
            int(job.job_id) for job in self._job_store.get_all() if job.job_id
        }
        self._output_claims.release_all_except(remaining_job_ids)
        return PurgeResult(
            deleted_job_count=len(deleted), kept_playlists=kept_playlists
        )

    def _descendants(self, job: Job) -> Iterator[Job]:
        if job.kind is not JobKind.EXPANSION or job.job_id is None:
            return
        for child in self._job_store.get_children(job.job_id):
            yield child
            yield from self._descendants(child)
