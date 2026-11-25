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
    PlaylistContext,
    PlaylistEntriesFound,
    PlaylistEntry,
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


def make_running_expansion(*, whole_playlist: bool = False) -> Job:
    """Expansión guardada como job 7 y enviada a un worker."""
    download_options = replace(make_download_options(), whole_playlist=whole_playlist)
    return replace(Job.new_expansion(URL, download_options), job_id=JobId(7)).start()


def make_entry(
    *, kind: JobKind = JobKind.DOWNLOAD, is_available: bool = True
) -> PlaylistEntry:
    """Tercera entrada de una playlist: un video o, con EXPANSION, otra lista."""
    return PlaylistEntry(
        url="https://media.example/watch?v=c",
        playlist_index=3,
        kind=kind,
        title="Entry c",
        media_key=(
            MediaKey(extractor_key="Example", media_id="c")
            if kind is JobKind.DOWNLOAD
            else None
        ),
        is_available=is_available,
    )


def child_of(
    parent: Job,
    playlist_entry: PlaylistEntry,
    *,
    is_duplicate: bool = False,
    playlist_title: str | None = "Mix",
    playlist_entry_count: int | None = None,
) -> Job:
    """Hijo de playlist_entry en un lote de la playlist PL1."""
    playlist_batch = PlaylistEntriesFound(
        playlist_id="PL1",
        playlist_title=playlist_title,
        playlist_entries=(playlist_entry,),
        playlist_entry_count=playlist_entry_count,
    )
    return Job.new_playlist_child(
        parent, playlist_batch, playlist_entry, is_duplicate=is_duplicate
    )


def test_playlist_child_is_a_pending_job_linked_to_its_playlist() -> None:
    child = child_of(make_running_expansion(), make_entry(), playlist_entry_count=12)

    assert child.job_id is None
    assert child.status is JobStatus.PENDING
    assert child.kind is JobKind.DOWNLOAD
    assert child.url == "https://media.example/watch?v=c"
    assert child.title == "Entry c"
    assert child.media_key == MediaKey(extractor_key="Example", media_id="c")
    assert child.parent_id == JobId(7)
    assert child.playlist_context == PlaylistContext(
        playlist_id="PL1",
        playlist_title="Mix",
        playlist_index=3,
        playlist_entry_count=12,
    )
    assert child.download_options.format_selector == "bv*+ba/b"


def test_entry_count_lower_than_the_index_is_treated_as_unknown() -> None:
    # El número de entradas que da el sitio puede estar desactualizado.
    child = child_of(make_running_expansion(), make_entry(), playlist_entry_count=2)

    assert child.playlist_context is not None
    assert child.playlist_context.playlist_entry_count is None


def test_nested_playlist_entry_becomes_a_pending_expansion() -> None:
    child = child_of(
        make_running_expansion(),
        make_entry(kind=JobKind.EXPANSION),
        playlist_title=None,
    )

    assert child.kind is JobKind.EXPANSION
    assert child.status is JobStatus.PENDING
    assert child.media_key is None


def test_child_does_not_inherit_the_whole_playlist_option() -> None:
    # --playlist decide sobre la URL encolada (ADR-0027), no sobre sus entradas.
    child = child_of(make_running_expansion(whole_playlist=True), make_entry())

    assert child.download_options.whole_playlist is False


def test_unavailable_entry_becomes_a_skipped_child() -> None:
    child = child_of(make_running_expansion(), make_entry(is_available=False))

    assert child.status is JobStatus.SKIPPED


def test_duplicate_entry_becomes_a_skipped_child() -> None:
    child = child_of(make_running_expansion(), make_entry(), is_duplicate=True)

    assert child.status is JobStatus.SKIPPED
    assert child.media_key == MediaKey(extractor_key="Example", media_id="c")


def test_only_a_stored_expansion_has_playlist_children() -> None:
    unstored = Job.new_expansion(URL, make_download_options())
    download = replace(make_running_expansion(), kind=JobKind.DOWNLOAD)

    with pytest.raises(ValueError, match="stored"):
        child_of(unstored, make_entry())
    with pytest.raises(ValueError, match="EXPANSION"):
        child_of(download, make_entry())


def test_running_job_interrupted_returns_to_pending() -> None:
    running = make_running_expansion()

    assert running.recover_from_interruption().status is JobStatus.PENDING


def test_job_interrupted_while_cancelling_ends_cancelled() -> None:
    cancelling = make_running_expansion().transition_to(
        JobStatus.CANCELLATION_REQUESTED
    )

    assert cancelling.recover_from_interruption().status is JobStatus.CANCELLED


@pytest.mark.parametrize(
    "status", [JobStatus.PENDING, JobStatus.COMPLETED, JobStatus.FAILED]
)
def test_only_an_interrupted_job_can_be_recovered(status: JobStatus) -> None:
    job = replace(make_running_expansion(), status=status)

    with pytest.raises(ValueError, match="interrupted"):
        job.recover_from_interruption()


def test_partial_files_of_a_job_live_in_a_folder_named_after_its_id() -> None:
    job = make_running_expansion()

    assert job.partial_directory() == Path("downloads", ".partial", "job-7")


def test_audio_only_job_keeps_its_partial_files_in_the_same_place() -> None:
    # La carpeta de parciales no depende del tipo de salida: el id ya es único.
    job = replace(
        make_running_expansion(),
        download_options=replace(make_download_options(), audio_only=True),
    )

    assert job.partial_directory() == Path("downloads", ".partial", "job-7")


def test_unstored_job_has_no_partial_folder() -> None:
    with pytest.raises(ValueError, match="stored"):
        Job.new_expansion(URL, make_download_options()).partial_directory()
