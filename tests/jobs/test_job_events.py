import dataclasses
import pickle
import subprocess
import sys
from typing import get_args

import pytest

from queued_media_downloader.jobs import (
    DownloadProgressed,
    FailureReason,
    FormatSelected,
    JobCancelled,
    JobCompleted,
    JobEvent,
    JobFailed,
    JobKind,
    JobStarted,
    MediaKey,
    PlaylistEntriesFound,
    PlaylistEntry,
    PostprocessingProgressed,
    PostprocessingStage,
    SingleMediaFound,
)

# Un ejemplo de cada job event de UC-03, con todos sus campos rellenos.
SAMPLE_JOB_EVENTS: list[JobEvent] = [
    JobStarted(),
    SingleMediaFound(
        media_key=MediaKey(extractor_key="Youtube", media_id="abc123"),
        title="Título con acentos",
    ),
    FormatSelected(selected_format_id="137+140"),
    DownloadProgressed(
        downloaded_bytes=1024,
        total_bytes=4096,
        bytes_per_second=512.5,
        eta_seconds=6,
    ),
    DownloadProgressed(
        downloaded_bytes=1024,
        total_bytes=None,
        bytes_per_second=None,
        eta_seconds=None,
    ),
    PostprocessingProgressed(
        postprocessor_name="Merger", postprocessing_stage=PostprocessingStage.STARTED
    ),
    JobCompleted(output_path="C:\\Users\\user\\Downloads\\video [abc123].mp4"),
    JobCompleted(output_path=None),
    JobFailed(failure_reason=FailureReason.NETWORK, failure_message="Timed out"),
    JobCancelled(),
    PlaylistEntriesFound(
        playlist_id="PL123",
        playlist_title="Favoritos con acentos",
        playlist_entries=(
            PlaylistEntry(
                url="https://media.example/watch?v=a",
                playlist_index=1,
                kind=JobKind.DOWNLOAD,
                title="Entrada a",
                media_key=MediaKey(extractor_key="Youtube", media_id="a"),
                is_available=True,
            ),
            PlaylistEntry(
                url="https://media.example/playlist?list=nested",
                playlist_index=2,
                kind=JobKind.EXPANSION,
                title=None,
                media_key=None,
                is_available=True,
            ),
            PlaylistEntry(
                url="https://media.example/watch?v=private",
                playlist_index=3,
                kind=JobKind.DOWNLOAD,
                title="[Private video]",
                media_key=MediaKey(extractor_key="Youtube", media_id="private"),
                is_available=False,
            ),
        ),
    ),
]

# Reconstruye los job events en un intérprete nuevo, como hace un worker
# arrancado con spawn, y los devuelve serializados de nuevo.
ECHO_THROUGH_NEW_INTERPRETER = (
    "import pickle, sys; pickle.dump(pickle.load(sys.stdin.buffer), sys.stdout.buffer)"
)


def test_every_job_event_type_has_a_sample() -> None:
    assert {type(job_event) for job_event in SAMPLE_JOB_EVENTS} == set(
        get_args(JobEvent)
    )


@pytest.mark.parametrize("job_event", SAMPLE_JOB_EVENTS, ids=repr)
def test_job_event_survives_serialization(job_event: JobEvent) -> None:
    assert pickle.loads(pickle.dumps(job_event)) == job_event


def test_job_events_travel_to_another_process_and_back() -> None:
    completed_process = subprocess.run(
        [sys.executable, "-c", ECHO_THROUGH_NEW_INTERPRETER],
        input=pickle.dumps(SAMPLE_JOB_EVENTS),
        capture_output=True,
        check=True,
    )

    assert pickle.loads(completed_process.stdout) == SAMPLE_JOB_EVENTS


@pytest.mark.parametrize(
    "job_event",
    [job_event for job_event in SAMPLE_JOB_EVENTS if dataclasses.fields(job_event)],
    ids=repr,
)
def test_job_event_cannot_be_modified(job_event: JobEvent) -> None:
    first_field = dataclasses.fields(job_event)[0].name

    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(job_event, first_field, None)
