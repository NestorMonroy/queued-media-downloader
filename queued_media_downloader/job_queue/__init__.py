"""Lo que el usuario hace con la cola: encolar, ejecutar, cancelar, reintentar."""

from queued_media_downloader.job_queue.cancel_job import CancelJob, CancelJobResult
from queued_media_downloader.job_queue.enqueue_media import (
    EnqueueMedia,
    InvalidUrlError,
)
from queued_media_downloader.job_queue.list_jobs import JobDetails, ListJobs, ShowJob
from queued_media_downloader.job_queue.purge_finished_jobs import (
    PurgeFinishedJobs,
    PurgeResult,
)
from queued_media_downloader.job_queue.recover_interrupted_jobs import (
    RecoverInterruptedJobs,
    RecoveryResult,
)
from queued_media_downloader.job_queue.retry_job import RetryJob, RetryJobResult
from queued_media_downloader.job_queue.run_queue import RunQueue, RunQueueResult

__all__ = [
    "CancelJob",
    "CancelJobResult",
    "EnqueueMedia",
    "InvalidUrlError",
    "JobDetails",
    "ListJobs",
    "PurgeFinishedJobs",
    "PurgeResult",
    "RecoverInterruptedJobs",
    "RecoveryResult",
    "RetryJob",
    "RetryJobResult",
    "RunQueue",
    "RunQueueResult",
    "ShowJob",
]
