from pathlib import Path

from queued_media_downloader.jobs import (
    DownloadOptions,
    FailureReason,
    Job,
    JobEvent,
    JobFailed,
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


def media_source(tmp_path: Path) -> YtDlpMediaSource:
    """MediaSource con caché en tmp_path y sin ffmpeg."""
    return YtDlpMediaSource(
        MediaSourceSettings(
            cache_directory=tmp_path / "cache",
            ffmpeg_location=None,
            max_filename_length=150,
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
