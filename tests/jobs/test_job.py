from pathlib import Path

import pytest

from queued_media_downloader.jobs import (
    DownloadOptions,
    InvalidJobTransitionError,
    Job,
    JobKind,
    JobStatus,
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
