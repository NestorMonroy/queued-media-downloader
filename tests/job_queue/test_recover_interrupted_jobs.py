from pathlib import Path

from queued_media_downloader.job_queue import (
    RecoverInterruptedJobs,
    RecoveryResult,
)
from queued_media_downloader.jobs import DownloadOptions, Job, JobId, JobStatus
from tests.doubles.in_memory_job_store import InMemoryJobStore

DOWNLOAD_OPTIONS = DownloadOptions(
    format_selector="bv*+ba/b",
    download_directory=Path("downloads"),
    output_template="%(title)s [%(id)s].%(ext)s",
    audio_only=False,
)

# Cómo llega cada job al arrancar run tras un cierre inesperado.
STATUS_PATHS: dict[JobStatus, tuple[JobStatus, ...]] = {
    JobStatus.PENDING: (),
    JobStatus.RUNNING: (JobStatus.RUNNING,),
    JobStatus.CANCELLATION_REQUESTED: (
        JobStatus.RUNNING,
        JobStatus.CANCELLATION_REQUESTED,
    ),
    JobStatus.COMPLETED: (JobStatus.RUNNING, JobStatus.COMPLETED),
    JobStatus.FAILED: (JobStatus.RUNNING, JobStatus.FAILED),
}


def job_store_with(*statuses: JobStatus) -> InMemoryJobStore:
    """Cola con un job por estado, en ese orden de creación."""
    job_store = InMemoryJobStore()
    for number, status in enumerate(statuses):
        job_id = job_store.create(
            Job.new_expansion(f"https://media.example/{number}", DOWNLOAD_OPTIONS)
        )
        job = job_store.get(job_id)
        for next_status in STATUS_PATHS[status]:
            job = job.transition_to(next_status)
        job_store.update(job)
    return job_store


def statuses_of(job_store: InMemoryJobStore) -> list[JobStatus]:
    return [job.status for job in job_store.all_jobs()]


def test_interrupted_jobs_are_requeued_or_cancelled() -> None:
    job_store = job_store_with(
        JobStatus.PENDING,
        JobStatus.RUNNING,
        JobStatus.CANCELLATION_REQUESTED,
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.RUNNING,
    )

    recovery_result = RecoverInterruptedJobs(job_store).execute()

    assert statuses_of(job_store) == [
        JobStatus.PENDING,
        JobStatus.PENDING,
        JobStatus.CANCELLED,
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.PENDING,
    ]
    assert recovery_result == RecoveryResult(
        requeued_job_count=2, cancelled_job_count=1
    )


def test_requeued_job_keeps_what_it_had_recorded() -> None:
    # La reanudación (T32) necesita el formato elegido en el primer intento.
    job_store = job_store_with(JobStatus.RUNNING)
    job_store.update(job_store.get(JobId(1)).record_selected_format("18"))

    RecoverInterruptedJobs(job_store).execute()

    assert job_store.get(JobId(1)).selected_format_id == "18"


def test_queue_without_interrupted_jobs_is_left_unchanged() -> None:
    job_store = job_store_with(JobStatus.PENDING, JobStatus.COMPLETED, JobStatus.FAILED)

    recovery_result = RecoverInterruptedJobs(job_store).execute()

    assert statuses_of(job_store) == [
        JobStatus.PENDING,
        JobStatus.COMPLETED,
        JobStatus.FAILED,
    ]
    assert recovery_result == RecoveryResult(
        requeued_job_count=0, cancelled_job_count=0
    )
    assert recovery_result.recovered_job_count == 0
