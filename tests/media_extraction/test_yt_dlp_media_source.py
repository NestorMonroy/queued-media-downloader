from dataclasses import replace
from pathlib import Path

from queued_media_downloader.jobs import (
    DownloadOptions,
    DownloadProgressed,
    FailureReason,
    FormatSelected,
    Job,
    JobCompleted,
    JobEvent,
    JobFailed,
    JobKind,
    MediaKey,
    SingleMediaFound,
)
from queued_media_downloader.media_extraction import MediaSourceSettings
from queued_media_downloader.media_extraction.yt_dlp_media_source import (
    YtDlpMediaSource,
)


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
    url: str, download_directory: Path, selected_format_id: str | None = None
) -> Job:
    """Job de descarga, como queda tras SingleMediaFound."""
    return replace(
        expansion_job(url, download_directory),
        kind=JobKind.DOWNLOAD,
        selected_format_id=selected_format_id,
    )


def media_source(tmp_path: Path) -> YtDlpMediaSource:
    """MediaSource con caché en tmp_path y sin ffmpeg."""
    return YtDlpMediaSource(
        MediaSourceSettings(
            cache_directory=tmp_path / "cache",
            ffmpeg_location=None,
            max_filename_length=150,
            progress_interval_seconds=0.5,
        )
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


def test_expanding_a_playlist_fails_as_unsupported_until_uc_04(
    local_media_server: str, tmp_path: Path
) -> None:
    published_events: list[JobEvent] = []
    job = expansion_job(f"{local_media_server}/two-videos.html", tmp_path)

    media_source(tmp_path).expand(job, published_events.append)

    [job_event] = published_events
    assert isinstance(job_event, JobFailed)
    assert job_event.failure_reason is FailureReason.UNSUPPORTED_URL
    assert "playlist" in job_event.failure_message


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


def test_download_reuses_the_format_selected_in_the_first_attempt(
    local_media_server: str, tmp_path: Path
) -> None:
    published_events: list[JobEvent] = []
    job = download_job(
        f"{local_media_server}/sample.mp4", tmp_path, selected_format_id="999"
    )

    media_source(tmp_path).download(job, published_events.append)

    [job_event] = published_events
    assert isinstance(job_event, JobFailed)
    assert "format" in job_event.failure_message


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
