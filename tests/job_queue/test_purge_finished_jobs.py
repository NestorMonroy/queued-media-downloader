from dataclasses import replace
from pathlib import Path

import pytest

from queued_media_downloader.job_queue import PurgeFinishedJobs
from queued_media_downloader.jobs import (
    DownloadOptions,
    Job,
    JobId,
    JobKind,
    JobStatus,
)
from tests.doubles.in_memory_job_store import InMemoryJobStore


def store(
    job_store: InMemoryJobStore,
    status: JobStatus,
    download_directory: Path,
    *,
    parent_id: int | None = None,
    kind: JobKind = JobKind.DOWNLOAD,
) -> JobId:
    options = DownloadOptions(
        format_selector="b",
        download_directory=download_directory,
        output_template="%(id)s.%(ext)s",
        audio_only=False,
    )
    job_id = job_store.create(
        replace(
            Job.new_expansion("https://media.example/x", options),
            kind=kind,
            parent_id=None if parent_id is None else JobId(parent_id),
        )
    )
    job_store.update(replace(job_store.get(job_id), status=status))
    return job_id


def remaining(job_store: InMemoryJobStore) -> list[int]:
    return [job.job_id for job in job_store.get_all() if job.job_id is not None]


@pytest.mark.parametrize(
    ("statuses", "expected_remaining"),
    [
        ({JobStatus.COMPLETED}, [2, 3, 4]),
        ({JobStatus.CANCELLED}, [1, 3, 4]),
        ({JobStatus.COMPLETED, JobStatus.CANCELLED}, [3, 4]),
    ],
)
def test_purge_deletes_only_the_chosen_finished_statuses(
    tmp_path: Path, statuses: set[JobStatus], expected_remaining: list[int]
) -> None:
    job_store = InMemoryJobStore()
    for status in (
        JobStatus.COMPLETED,
        JobStatus.CANCELLED,
        JobStatus.FAILED,
        JobStatus.PENDING,
    ):
        store(job_store, status, tmp_path)

    PurgeFinishedJobs(job_store).execute(statuses)

    assert remaining(job_store) == expected_remaining


def test_playlist_with_an_unfinished_entry_is_kept(tmp_path: Path) -> None:
    # Borrarla arrastraría a su entrada pendiente (ON DELETE CASCADE).
    job_store = InMemoryJobStore()
    playlist = store(job_store, JobStatus.COMPLETED, tmp_path, kind=JobKind.EXPANSION)
    store(job_store, JobStatus.COMPLETED, tmp_path, parent_id=playlist)
    store(job_store, JobStatus.PENDING, tmp_path, parent_id=playlist)

    result = PurgeFinishedJobs(job_store).execute({JobStatus.COMPLETED})

    assert [job.job_id for job in result.kept_playlists] == [playlist]
    assert remaining(job_store) == [1, 3]


def test_finished_playlist_goes_with_its_entries_and_duplicates(tmp_path: Path) -> None:
    job_store = InMemoryJobStore()
    playlist = store(job_store, JobStatus.COMPLETED, tmp_path, kind=JobKind.EXPANSION)
    store(job_store, JobStatus.COMPLETED, tmp_path, parent_id=playlist)
    store(job_store, JobStatus.SKIPPED, tmp_path, parent_id=playlist)

    result = PurgeFinishedJobs(job_store).execute({JobStatus.COMPLETED})

    assert result.deleted_job_count == 3
    assert remaining(job_store) == []


def test_purge_removes_partial_files_but_never_downloaded_files(tmp_path: Path) -> None:
    job_store = InMemoryJobStore()
    cancelled = store(job_store, JobStatus.CANCELLED, tmp_path)
    partial_directory = job_store.get(cancelled).partial_directory()
    partial_directory.mkdir(parents=True)
    (partial_directory / "video.mp4.part").write_bytes(b"partial")
    downloaded = tmp_path / "video [abc].mp4"
    downloaded.write_bytes(b"finished")

    PurgeFinishedJobs(job_store).execute({JobStatus.CANCELLED})

    assert not partial_directory.exists()
    assert downloaded.read_bytes() == b"finished"


def test_unfinished_statuses_cannot_be_purged() -> None:
    with pytest.raises(ValueError, match="purged"):
        PurgeFinishedJobs(InMemoryJobStore()).execute({JobStatus.FAILED})
