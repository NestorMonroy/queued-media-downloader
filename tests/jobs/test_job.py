from dataclasses import replace
from pathlib import Path

import pytest

from queued_media_downloader.jobs import (
    DownloadOptions,
    FailureReason,
    InvalidJobTransitionError,
    Job,
    JobId,
    JobKind,
    JobStatus,
    MediaKey,
)

URL = "https://media.example/watch?v=abc123"


def make_download_options() -> DownloadOptions:
    return DownloadOptions(
        format_selector="bv*+ba/b",
        download_directory=Path("downloads"),
        output_template="%(title)s [%(id)s].%(ext)s",
        audio_only=False,
    )


def test_new_expansion_job_is_pending_and_not_yet_stored() -> None:
    download_options = make_download_options()

    job = Job.new_expansion(URL, download_options)

    assert job.kind is JobKind.EXPANSION
    assert job.status is JobStatus.PENDING
    assert job.url == URL
    assert job.download_options == download_options
    assert job.job_id is None
    assert job.media_key is None
    assert job.attempt_count == 0


def test_allowed_transition_returns_a_copy_with_the_new_status() -> None:
    pending_job = Job.new_expansion(URL, make_download_options())

    running_job = pending_job.transition_to(JobStatus.RUNNING)

    assert running_job.status is JobStatus.RUNNING
    assert pending_job.status is JobStatus.PENDING
    assert running_job.url == pending_job.url


def test_rejected_transition_raises_and_leaves_the_job_unchanged() -> None:
    pending_job = Job.new_expansion(URL, make_download_options())

    with pytest.raises(InvalidJobTransitionError):
        pending_job.transition_to(JobStatus.COMPLETED)

    assert pending_job.status is JobStatus.PENDING


RUNNING_EXPANSION = replace(
    Job.new_expansion(URL, make_download_options()),
    job_id=JobId(1),
    status=JobStatus.RUNNING,
)
MEDIA_KEY = MediaKey(extractor_key="Youtube", media_id="abc123")


def test_start_moves_a_pending_job_to_running() -> None:
    job = Job.new_expansion(URL, make_download_options())

    assert job.start().status is JobStatus.RUNNING


def test_single_media_found_turns_the_expansion_into_a_pending_download() -> None:
    job = RUNNING_EXPANSION.found_single_media(MEDIA_KEY, "Title")

    assert job.kind is JobKind.DOWNLOAD
    assert job.status is JobStatus.PENDING
    assert job.media_key == MEDIA_KEY
    assert job.title == "Title"


def test_duplicate_single_media_is_skipped_as_a_download() -> None:
    job = RUNNING_EXPANSION.skip_as_duplicate(MEDIA_KEY, "Title")

    assert job.kind is JobKind.DOWNLOAD
    assert job.status is JobStatus.SKIPPED
    assert job.media_key == MEDIA_KEY


def test_only_an_expansion_can_find_its_single_media() -> None:
    running_download = RUNNING_EXPANSION.found_single_media(MEDIA_KEY, "T").start()

    with pytest.raises(ValueError, match="EXPANSION"):
        running_download.found_single_media(MEDIA_KEY, "T")


def test_selected_format_is_recorded_without_changing_the_status() -> None:
    job = RUNNING_EXPANSION.record_selected_format("137+140")

    assert job.selected_format_id == "137+140"
    assert job.status is JobStatus.RUNNING


def test_complete_records_the_output_path() -> None:
    job = RUNNING_EXPANSION.complete("downloads/video.mp4")

    assert job.status is JobStatus.COMPLETED
    assert job.output_path == "downloads/video.mp4"


def test_fail_records_the_reason_and_message() -> None:
    job = RUNNING_EXPANSION.fail(FailureReason.NETWORK, "Timed out")

    assert job.status is JobStatus.FAILED
    assert job.failure_reason is FailureReason.NETWORK
    assert job.failure_message == "Timed out"


def test_cancellation_cannot_be_confirmed_unless_it_was_requested() -> None:
    with pytest.raises(InvalidJobTransitionError):
        RUNNING_EXPANSION.confirm_cancellation()
