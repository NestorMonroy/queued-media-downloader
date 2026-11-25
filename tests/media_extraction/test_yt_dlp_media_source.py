from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from yt_dlp import YoutubeDL
from yt_dlp.utils import PostProcessingError

from queued_media_downloader.jobs import (
    DownloadOptions,
    DownloadProgressed,
    FailureReason,
    FormatSelected,
    Job,
    JobCompleted,
    JobEvent,
    JobFailed,
    JobId,
    JobKind,
    MediaKey,
    PlaylistContext,
    PlaylistEntriesFound,
    PlaylistEntry,
    SingleMediaFound,
)
from queued_media_downloader.media_extraction import MediaSourceSettings
from queued_media_downloader.media_extraction import (
    yt_dlp_media_source as yt_dlp_media_source_module,
)
from queued_media_downloader.media_extraction.recording_postprocessors import (
    FinalPathRecorder,
)
from queued_media_downloader.media_extraction.yt_dlp_expansion import (
    playlist_entry_count_of,
)
from queued_media_downloader.media_extraction.yt_dlp_media_source import (
    YtDlpMediaSource,
)
from tests.conftest import SAMPLE_MEDIA_CONTENT


def expansion_job(url: str, download_directory: Path) -> Job:
    """Job de expansión para url que descargaría en download_directory."""
    return Job.new_expansion(
        url,
        DownloadOptions(
            format_selector="bv*+ba/b",
            download_directory=download_directory,
            output_template="%(title)s [%(id)s].%(ext)s",
            audio_only=False,
        ),
    )


def download_job(
    url: str,
    download_directory: Path,
    selected_format_id: str | None = None,
    job_id: int = 1,
) -> Job:
    """Job de descarga guardado como job_id, como queda tras SingleMediaFound."""
    return replace(
        expansion_job(url, download_directory),
        job_id=JobId(job_id),
        kind=JobKind.DOWNLOAD,
        selected_format_id=selected_format_id,
    )


def partial_directory(download_directory: Path, job_id: int = 1) -> Path:
    """Carpeta de parciales de un job (Job.partial_directory)."""
    return download_directory / ".partial" / f"job-{job_id}"


def media_source(
    tmp_path: Path, playlist_batch_size: int = 50, max_filename_length: int = 150
) -> YtDlpMediaSource:
    """MediaSource con caché en tmp_path y sin ffmpeg."""
    return YtDlpMediaSource(
        MediaSourceSettings(
            cache_directory=tmp_path / "cache",
            ffmpeg_location=None,
            max_filename_length=max_filename_length,
            progress_interval_seconds=0.5,
            playlist_batch_size=playlist_batch_size,
        )
    )


def feed_entry(
    local_media_server: str, name: str, playlist_index: int, title: str
) -> PlaylistEntry:
    """Entrada de un feed local: sin extractor conocido, se expande al descargar."""
    return PlaylistEntry(
        url=f"{local_media_server}/{name}",
        playlist_index=playlist_index,
        kind=JobKind.EXPANSION,
        title=title,
        media_key=None,
        is_available=True,
    )


def test_expanding_a_single_media_url_publishes_single_media_found(
    local_media_server: str, tmp_path: Path
) -> None:
    published_events: list[JobEvent] = []
    job = expansion_job(f"{local_media_server}/sample.mp4", tmp_path / "downloads")

    media_source(tmp_path).expand(job, published_events.append)

    assert published_events == [
        SingleMediaFound(
            media_key=MediaKey(extractor_key="Generic", media_id="sample"),
            title="sample",
        )
    ]


def test_expanding_does_not_download(local_media_server: str, tmp_path: Path) -> None:
    download_directory = tmp_path / "downloads"
    job = expansion_job(f"{local_media_server}/sample.mp4", download_directory)
    published_events: list[JobEvent] = []

    media_source(tmp_path).expand(job, published_events.append)

    assert not download_directory.exists() or not any(download_directory.iterdir())


def test_expanding_a_playlist_publishes_its_entries_in_batches(
    local_media_server: str, tmp_path: Path
) -> None:
    published_events: list[JobEvent] = []
    feed_url = f"{local_media_server}/feed.xml"

    media_source(tmp_path, playlist_batch_size=2).expand(
        expansion_job(feed_url, tmp_path), published_events.append
    )

    assert published_events == [
        PlaylistEntriesFound(
            playlist_id=feed_url,
            playlist_title="Local feed",
            playlist_entries=(
                feed_entry(local_media_server, "sample.mp4", 1, "Video A"),
                feed_entry(local_media_server, "other.mp4", 2, "Video B"),
            ),
        ),
        PlaylistEntriesFound(
            playlist_id=feed_url,
            playlist_title="Local feed",
            playlist_entries=(
                feed_entry(local_media_server, "nested.xml", 3, "Nested"),
            ),
        ),
        JobCompleted(output_path=None),
    ]


def test_expanding_a_redirect_follows_it_to_the_media(
    local_media_server: str, tmp_path: Path
) -> None:
    published_events: list[JobEvent] = []
    job = expansion_job(f"{local_media_server}/redirect.html", tmp_path)

    media_source(tmp_path).expand(job, published_events.append)

    [job_event] = published_events
    assert isinstance(job_event, SingleMediaFound)
    assert job_event.media_key == MediaKey(extractor_key="Generic", media_id="sample")


def test_playlist_whose_entries_have_no_url_of_their_own_fails(
    local_media_server: str, tmp_path: Path
) -> None:
    # Videos incrustados en una página: yt-dlp los enumera, pero ninguno tiene
    # una URL propia con la que crear un job hijo.
    published_events: list[JobEvent] = []
    job = expansion_job(f"{local_media_server}/two-videos.html", tmp_path)

    media_source(tmp_path).expand(job, published_events.append)

    [job_event] = published_events
    assert isinstance(job_event, JobFailed)
    assert job_event.failure_reason is FailureReason.UNSUPPORTED_URL
    assert "2 playlist entries" in job_event.failure_message


def test_expanding_a_missing_url_publishes_job_failed(
    local_media_server: str, tmp_path: Path
) -> None:
    published_events: list[JobEvent] = []
    job = expansion_job(f"{local_media_server}/missing.mp4", tmp_path)

    media_source(tmp_path).expand(job, published_events.append)

    [job_event] = published_events
    assert isinstance(job_event, JobFailed)
    assert job_event.failure_reason is FailureReason.UNAVAILABLE


def test_download_writes_the_file_and_publishes_its_final_path(
    local_media_server: str, tmp_path: Path
) -> None:
    published_events: list[JobEvent] = []
    download_directory = tmp_path / "downloads"
    job = download_job(f"{local_media_server}/sample.mp4", download_directory)

    media_source(tmp_path).download(job, published_events.append)

    output_path = download_directory / "sample [sample].mp4"
    assert output_path.read_bytes() == (tmp_path / "served/sample.mp4").read_bytes()
    assert published_events[0] == FormatSelected(selected_format_id="mp4")
    assert any(isinstance(event, DownloadProgressed) for event in published_events)
    assert published_events[-1] == JobCompleted(output_path=str(output_path))


def test_playlist_child_is_downloaded_into_its_playlist_folder(
    local_media_server: str, tmp_path: Path
) -> None:
    published_events: list[JobEvent] = []
    download_directory = tmp_path / "downloads"
    job = replace(
        download_job(f"{local_media_server}/sample.mp4", download_directory),
        playlist_context=PlaylistContext(
            playlist_id="PL1",
            playlist_title="Local feed",
            playlist_index=2,
            playlist_entry_count=3,
        ),
    )

    media_source(tmp_path).download(job, published_events.append)

    output_path = download_directory / "Local feed" / "2 - sample [sample].mp4"
    assert output_path.is_file()
    assert published_events[-1] == JobCompleted(output_path=str(output_path))


@pytest.fixture
def requested_formats(monkeypatch: pytest.MonkeyPatch) -> list[str | None]:
    """Formato que pide cada intento de descarga, en orden."""
    formats: list[str | None] = []

    class FormatRecordingYoutubeDL(YoutubeDL):  # type: ignore[misc]
        def __init__(self, params: dict[str, Any]) -> None:
            formats.append(params.get("format"))
            super().__init__(params)

    monkeypatch.setattr(
        yt_dlp_media_source_module, "YoutubeDL", FormatRecordingYoutubeDL
    )
    return formats


def test_interrupted_download_continues_from_its_partial_file(
    local_media_server: str,
    tmp_path: Path,
    media_requests: list[tuple[str, str | None]],
) -> None:
    # Lo que deja un run interrumpido: el .part del job, en su carpeta.
    published_events: list[JobEvent] = []
    partial_path = partial_directory(tmp_path) / "sample [sample].mp4.part"
    partial_path.parent.mkdir(parents=True)
    partial_path.write_bytes(SAMPLE_MEDIA_CONTENT[:5000])
    job = download_job(
        f"{local_media_server}/sample.mp4", tmp_path, selected_format_id="mp4"
    )

    media_source(tmp_path).download(job, published_events.append)

    output_path = tmp_path / "sample [sample].mp4"
    assert media_requests == [
        # Extracción: yt-dlp vuelve a extraer la URL (UC-06, paso 6); con un
        # enlace directo, el extractor genérico lee 512 bytes (generic.py:892).
        ("/sample.mp4", None),
        # Descarga: solo los bytes que faltan.
        ("/sample.mp4", "bytes=5000-"),
    ]
    assert output_path.read_bytes() == SAMPLE_MEDIA_CONTENT
    assert not partial_directory(tmp_path).exists()
    assert published_events[-1] == JobCompleted(output_path=str(output_path))


def test_download_writes_intermediate_files_only_in_its_partial_directory(
    local_media_server: str, tmp_path: Path
) -> None:
    seen_partial_paths: list[Path] = []

    def record_partial_path(job_event: JobEvent) -> None:
        if isinstance(job_event, DownloadProgressed):
            seen_partial_paths.extend(
                path for path in tmp_path.rglob("*.part") if path.is_file()
            )

    job = download_job(f"{local_media_server}/sample.mp4", tmp_path)

    media_source(tmp_path).download(job, record_partial_path)

    assert seen_partial_paths
    assert {path.parent for path in seen_partial_paths} == {partial_directory(tmp_path)}


def test_finished_download_run_again_completes_without_downloading(
    local_media_server: str,
    tmp_path: Path,
    media_requests: list[tuple[str, str | None]],
) -> None:
    # Un cierre entre la descarga y JobCompleted deja el job RUNNING con el
    # archivo ya terminado: la recuperación lo vuelve a enviar.
    job = download_job(
        f"{local_media_server}/sample.mp4", tmp_path, selected_format_id="mp4"
    )
    first_run_events: list[JobEvent] = []
    media_source(tmp_path).download(job, first_run_events.append)
    media_requests.clear()
    published_events: list[JobEvent] = []

    media_source(tmp_path).download(job, published_events.append)

    output_path = tmp_path / "sample [sample].mp4"
    assert media_requests == [("/sample.mp4", None)]
    assert output_path.read_bytes() == SAMPLE_MEDIA_CONTENT
    assert published_events[-1] == JobCompleted(output_path=str(output_path))


def test_leftovers_of_an_interrupted_cleanup_go_with_the_next_completion(
    local_media_server: str, tmp_path: Path
) -> None:
    # Cierre tras guardar el formato nuevo y antes de limpiar: quedan el
    # archivo terminado y los parciales del formato abandonado (§4 de T44).
    job = download_job(
        f"{local_media_server}/sample.mp4", tmp_path, selected_format_id="mp4"
    )
    first_run_events: list[JobEvent] = []
    media_source(tmp_path).download(job, first_run_events.append)
    abandoned_partial = partial_directory(tmp_path) / "sample [sample].f999.webm.part"
    abandoned_partial.parent.mkdir(parents=True)
    abandoned_partial.write_bytes(b"abandoned format")
    published_events: list[JobEvent] = []

    media_source(tmp_path).download(job, published_events.append)
    media_source(tmp_path).download(job, published_events.append)

    assert not partial_directory(tmp_path).exists()
    assert published_events[-1] == JobCompleted(
        output_path=str(tmp_path / "sample [sample].mp4")
    )


def test_unavailable_saved_format_is_retried_once_with_the_original_selector(
    local_media_server: str, tmp_path: Path, requested_formats: list[str | None]
) -> None:
    # A1: el formato del primer intento (999) ya no se ofrece.
    published_events: list[JobEvent] = []
    abandoned_partial = partial_directory(tmp_path) / "sample [sample].webm.part"
    abandoned_partial.parent.mkdir(parents=True)
    abandoned_partial.write_bytes(b"abandoned format")
    job = download_job(
        f"{local_media_server}/sample.mp4", tmp_path, selected_format_id="999"
    )

    media_source(tmp_path).download(job, published_events.append)

    output_path = tmp_path / "sample [sample].mp4"
    assert requested_formats == ["999", "bv*+ba/b"]
    assert FormatSelected(selected_format_id="mp4") in published_events
    assert published_events[-1] == JobCompleted(output_path=str(output_path))
    assert output_path.read_bytes() == SAMPLE_MEDIA_CONTENT
    assert not partial_directory(tmp_path).exists()


@pytest.mark.parametrize(
    ("output_template", "shared_partial_name"),
    [
        # Plantilla sin %(id)s: dos contenidos, el mismo nombre.
        ("video.%(ext)s", "video.mp4.part"),
        # Título recortado por max_filename_length (5): el [id] se pierde.
        ("%(title)s [%(id)s].%(ext)s", "other.mp4.part"),
    ],
    ids=["template without id", "trimmed name"],
)
def test_completion_never_touches_partial_files_of_another_job(
    local_media_server: str,
    tmp_path: Path,
    output_template: str,
    shared_partial_name: str,
) -> None:
    # R-14: el job 1 tiene a medias otro contenido con el mismo nombre de
    # archivo que el job 2, que abandona un formato y termina.
    other_job_partial = partial_directory(tmp_path, job_id=1) / shared_partial_name
    other_job_partial.parent.mkdir(parents=True)
    other_job_partial.write_bytes(SAMPLE_MEDIA_CONTENT[:5000])
    job = download_job(
        f"{local_media_server}/other.mp4", tmp_path, selected_format_id="999", job_id=2
    )
    job = replace(
        job,
        download_options=replace(job.download_options, output_template=output_template),
    )
    published_events: list[JobEvent] = []

    media_source(tmp_path, max_filename_length=5).download(job, published_events.append)

    completed = published_events[-1]
    assert isinstance(completed, JobCompleted)
    # Los dos jobs dan de verdad el mismo nombre a su archivo.
    assert Path(str(completed.output_path)).name == shared_partial_name.removesuffix(
        ".part"
    )
    assert other_job_partial.read_bytes() == SAMPLE_MEDIA_CONTENT[:5000]
    assert not partial_directory(tmp_path, job_id=2).exists()


def test_failed_retry_publishes_one_failure_and_is_not_retried_again(
    local_media_server: str, tmp_path: Path, requested_formats: list[str | None]
) -> None:
    published_events: list[JobEvent] = []
    partial_path = partial_directory(tmp_path) / "sample [sample].webm.part"
    partial_path.parent.mkdir(parents=True)
    partial_path.write_bytes(b"maybe still useful")
    job = download_job(
        f"{local_media_server}/sample.mp4", tmp_path, selected_format_id="999"
    )
    job = replace(
        job, download_options=replace(job.download_options, format_selector="777")
    )

    media_source(tmp_path).download(job, published_events.append)

    assert requested_formats == ["999", "777"]
    [job_event] = published_events
    assert isinstance(job_event, JobFailed)
    assert job_event.failure_reason is FailureReason.UNAVAILABLE
    # Sin una descarga terminada, nada se limpia: el .part puede servir aún.
    assert partial_path.exists()


def test_other_failure_with_a_saved_format_is_not_retried(
    local_media_server: str, tmp_path: Path, requested_formats: list[str | None]
) -> None:
    published_events: list[JobEvent] = []
    job = download_job(
        f"{local_media_server}/missing.mp4", tmp_path, selected_format_id="mp4"
    )

    media_source(tmp_path).download(job, published_events.append)

    assert requested_formats == ["mp4"]
    [job_event] = published_events
    assert isinstance(job_event, JobFailed)
    assert job_event.failure_reason is FailureReason.UNAVAILABLE


def test_download_without_an_output_file_is_not_completed(
    local_media_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    published_events: list[JobEvent] = []

    def download_nothing(youtube_dl: YoutubeDL, urls: list[str]) -> int:  # noqa: ARG001
        return 0

    monkeypatch.setattr(YoutubeDL, "download", download_nothing)
    job = download_job(f"{local_media_server}/sample.mp4", tmp_path)

    media_source(tmp_path).download(job, published_events.append)

    assert published_events == [
        JobFailed(
            failure_reason=FailureReason.FILESYSTEM,
            failure_message="The download finished without an output file",
        )
    ]


def test_download_with_a_non_zero_return_code_is_not_completed(
    local_media_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # yt-dlp devuelve 1 si informó de errores sin lanzar una excepción.
    published_events: list[JobEvent] = []
    original_download = YoutubeDL.download

    def download_reporting_errors(youtube_dl: YoutubeDL, urls: list[str]) -> int:
        original_download(youtube_dl, urls)
        return 1

    monkeypatch.setattr(YoutubeDL, "download", download_reporting_errors)
    job = download_job(f"{local_media_server}/sample.mp4", tmp_path)

    media_source(tmp_path).download(job, published_events.append)

    assert not any(isinstance(event, JobCompleted) for event in published_events)
    assert published_events[-1] == JobFailed(
        failure_reason=FailureReason.UNKNOWN,
        failure_message="yt-dlp reported errors (return code 1)",
    )


def test_failed_postprocessing_is_not_completed(
    local_media_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    published_events: list[JobEvent] = []

    def failing_post_process(youtube_dl: YoutubeDL, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG001
        raise PostProcessingError("Conversion failed!")

    monkeypatch.setattr(YoutubeDL, "post_process", failing_post_process)
    job = download_job(f"{local_media_server}/sample.mp4", tmp_path)

    media_source(tmp_path).download(job, published_events.append)

    assert not any(isinstance(event, JobCompleted) for event in published_events)
    [failure] = [event for event in published_events if isinstance(event, JobFailed)]
    assert failure.failure_reason is FailureReason.POSTPROCESSING


def test_download_whose_output_file_is_empty_is_not_completed(
    local_media_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    published_events: list[JobEvent] = []
    empty_path = tmp_path / "empty.mp4"
    empty_path.touch()

    def record_empty_file(
        recorder: FinalPathRecorder, info: dict[str, Any]
    ) -> tuple[list[str], dict[str, Any]]:
        recorder.final_path = str(empty_path)
        return [], info

    monkeypatch.setattr(FinalPathRecorder, "run", record_empty_file)
    job = download_job(f"{local_media_server}/sample.mp4", tmp_path)

    media_source(tmp_path).download(job, published_events.append)

    assert published_events[-1] == JobFailed(
        failure_reason=FailureReason.FILESYSTEM,
        failure_message=f"The output file is missing or empty: {empty_path}",
    )


def test_output_file_left_in_the_partial_directory_is_not_completed(
    local_media_server: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    published_events: list[JobEvent] = []
    unmoved_path = partial_directory(tmp_path) / "sample [sample].mp4"

    def record_unmoved_file(
        recorder: FinalPathRecorder, info: dict[str, Any]
    ) -> tuple[list[str], dict[str, Any]]:
        unmoved_path.parent.mkdir(parents=True, exist_ok=True)
        unmoved_path.write_bytes(b"data")
        recorder.final_path = str(unmoved_path)
        return [], info

    monkeypatch.setattr(FinalPathRecorder, "run", record_unmoved_file)
    job = download_job(f"{local_media_server}/sample.mp4", tmp_path)

    media_source(tmp_path).download(job, published_events.append)

    last_event = published_events[-1]
    assert isinstance(last_event, JobFailed)
    assert "not moved out of its partial directory" in last_event.failure_message


def test_download_of_a_missing_url_publishes_job_failed(
    local_media_server: str, tmp_path: Path
) -> None:
    published_events: list[JobEvent] = []
    job = download_job(f"{local_media_server}/missing.mp4", tmp_path)

    media_source(tmp_path).download(job, published_events.append)

    assert published_events == [
        JobFailed(
            failure_reason=FailureReason.UNAVAILABLE,
            failure_message=(
                "[generic] missing: Unable to download webpage: "
                "HTTP Error 404: File not found"
            ),
        )
    ]


@pytest.mark.network
def test_video_link_inside_a_youtube_list_expands_to_the_video_only(
    tmp_path: Path,
) -> None:
    published_events: list[JobEvent] = []
    job = expansion_job(
        "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        "&list=PLbpi6ZahtOH6Blw3RGYpWkSByi_T7Rygb",
        tmp_path,
    )

    media_source(tmp_path).expand(job, published_events.append)

    [job_event] = published_events
    assert isinstance(job_event, SingleMediaFound)
    assert job_event.media_key == MediaKey(
        extractor_key="Youtube", media_id="jNQXAC9IVRw"
    )


@pytest.mark.network
def test_video_link_inside_a_list_expands_the_whole_list_with_the_option(
    tmp_path: Path,
) -> None:
    published_events: list[JobEvent] = []
    job = expansion_job(
        "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        "&list=PLbpi6ZahtOH6Blw3RGYpWkSByi_T7Rygb",
        tmp_path,
    )
    job = replace(
        job, download_options=replace(job.download_options, whole_playlist=True)
    )

    media_source(tmp_path).expand(job, published_events.append)

    assert isinstance(published_events[0], PlaylistEntriesFound)
    assert isinstance(published_events[-1], JobCompleted)


class StopExpansion(BaseException):
    """Detiene la expansión desde publish; no la captura el except Exception."""


@pytest.mark.network
def test_large_channel_is_expanded_lazily_page_by_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # R-06: con process=False, el primer lote llega tras pocas peticiones, no
    # tras descargar todas las páginas de un canal con miles de videos.
    request_count = 0
    original_urlopen = YoutubeDL.urlopen

    def counting_urlopen(youtube_dl: YoutubeDL, request: object) -> object:
        nonlocal request_count
        request_count += 1
        return original_urlopen(youtube_dl, request)

    def stop_after_the_first_batch(job_event: JobEvent) -> None:
        if isinstance(job_event, PlaylistEntriesFound):
            raise StopExpansion(job_event)

    monkeypatch.setattr(YoutubeDL, "urlopen", counting_urlopen)
    job = expansion_job("https://www.youtube.com/@YouTube/videos", tmp_path)

    with pytest.raises(StopExpansion) as stopped:
        media_source(tmp_path).expand(job, stop_after_the_first_batch)

    [first_batch] = stopped.value.args
    assert len(first_batch.playlist_entries) == 50
    assert all(entry.kind is JobKind.DOWNLOAD for entry in first_batch.playlist_entries)
    assert request_count < 10


@pytest.mark.parametrize(
    ("playlist_count", "expected"), [(12, 12), (None, None), ("12", None), (-1, None)]
)
def test_entry_count_is_taken_only_when_the_site_reports_it(
    playlist_count: object, expected: int | None
) -> None:
    assert playlist_entry_count_of({"playlist_count": playlist_count}) == expected
