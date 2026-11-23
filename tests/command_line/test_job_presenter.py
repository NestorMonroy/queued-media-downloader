import io

import pytest

from queued_media_downloader.command_line.job_presenter import JobPresenter
from queued_media_downloader.jobs import (
    DownloadProgressed,
    FailureReason,
    FormatSelected,
    JobCancelled,
    JobCompleted,
    JobEvent,
    JobFailed,
    JobId,
    JobStarted,
    MediaKey,
    PostprocessingProgressed,
    PostprocessingStage,
    SingleMediaFound,
)
from queued_media_downloader.workers import WorkerMessage


def presented_line(job_event: JobEvent) -> str:
    """Texto que el presentador escribe para job_event del job 7."""
    output = io.StringIO()
    JobPresenter(output).present(
        WorkerMessage(
            worker_id=1, job_id=JobId(7), sequence_number=1, job_event=job_event
        )
    )
    return output.getvalue()


@pytest.mark.parametrize(
    ("job_event", "expected_line"),
    [
        (JobStarted(), "Job 7: started\n"),
        (
            SingleMediaFound(
                media_key=MediaKey(extractor_key="Youtube", media_id="a"),
                title="A title",
            ),
            "Job 7: found 'A title'\n",
        ),
        (FormatSelected(selected_format_id="137+140"), "Job 7: format 137+140\n"),
        (
            DownloadProgressed(
                downloaded_bytes=1_572_864,
                total_bytes=3_145_728,
                bytes_per_second=524_288.0,
                eta_seconds=3,
            ),
            "Job 7: 50.0% of 3.0 MiB at 512.0 KiB/s, ETA 3 s\n",
        ),
        (
            DownloadProgressed(
                downloaded_bytes=2048,
                total_bytes=None,
                bytes_per_second=None,
                eta_seconds=None,
            ),
            "Job 7: 2.0 KiB downloaded\n",
        ),
        (
            PostprocessingProgressed(
                postprocessor_name="Merger",
                postprocessing_stage=PostprocessingStage.STARTED,
            ),
            "Job 7: running Merger\n",
        ),
        (
            JobCompleted(output_path="downloads/a [a].mp4"),
            "Job 7: completed, saved to downloads/a [a].mp4\n",
        ),
        (JobCompleted(output_path=None), "Job 7: completed\n"),
        (
            JobFailed(failure_reason=FailureReason.NETWORK, failure_message="Reset"),
            "Job 7: failed (NETWORK): Reset\n",
        ),
        (JobCancelled(), "Job 7: cancelled\n"),
    ],
    ids=lambda value: type(value).__name__ if not isinstance(value, str) else "",
)
def test_job_event_is_presented_as_one_line_in_english(
    job_event: JobEvent, expected_line: str
) -> None:
    assert presented_line(job_event) == expected_line


@pytest.mark.parametrize(
    "postprocessing_stage",
    [PostprocessingStage.PROCESSING, PostprocessingStage.FINISHED],
)
def test_only_the_start_of_a_postprocessor_is_presented(
    postprocessing_stage: PostprocessingStage,
) -> None:
    job_event = PostprocessingProgressed(
        postprocessor_name="Merger", postprocessing_stage=postprocessing_stage
    )

    assert presented_line(job_event) == ""
