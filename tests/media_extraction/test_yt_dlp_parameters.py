import logging
from pathlib import Path

import pytest
from yt_dlp import YoutubeDL

from queued_media_downloader.jobs import DownloadOptions
from queued_media_downloader.media_extraction import MediaSourceSettings
from queued_media_downloader.media_extraction.yt_dlp_parameters import (
    YtDlpLogger,
    build_yt_dlp_parameters,
)

DOWNLOAD_OPTIONS = DownloadOptions(
    format_selector="bv*+ba/b",
    download_directory=Path("downloads"),
    output_template="%(title)s [%(id)s].%(ext)s",
    audio_only=False,
)
MEDIA_SOURCE_SETTINGS = MediaSourceSettings(
    cache_directory=Path("state/yt-dlp-cache"),
    ffmpeg_location=Path("vendor/ffmpeg/bin"),
    max_filename_length=150,
)


def test_parameters_carry_the_job_options_and_the_fixed_values() -> None:
    parameters = build_yt_dlp_parameters(DOWNLOAD_OPTIONS, MEDIA_SOURCE_SETTINGS)

    assert parameters["format"] == "bv*+ba/b"
    assert parameters["paths"] == {"home": "downloads"}
    assert parameters["outtmpl"] == {"default": "%(title)s [%(id)s].%(ext)s"}
    assert parameters["cachedir"] == str(Path("state/yt-dlp-cache"))
    assert parameters["ffmpeg_location"] == str(Path("vendor/ffmpeg/bin"))
    assert parameters["trim_file_name"] == 150
    assert parameters["js_runtimes"] == {"deno": {}}
    assert parameters["continuedl"] is True
    assert parameters["noprogress"] is True
    assert isinstance(parameters["logger"], YtDlpLogger)


def test_ffmpeg_location_is_omitted_when_unknown() -> None:
    settings_without_ffmpeg = MediaSourceSettings(
        cache_directory=Path("cache"), ffmpeg_location=None, max_filename_length=150
    )

    parameters = build_yt_dlp_parameters(DOWNLOAD_OPTIONS, settings_without_ffmpeg)

    assert "ffmpeg_location" not in parameters


def test_pinned_yt_dlp_accepts_the_parameters() -> None:
    parameters = build_yt_dlp_parameters(DOWNLOAD_OPTIONS, MEDIA_SOURCE_SETTINGS)

    with YoutubeDL(parameters) as youtube_dl:
        assert (
            youtube_dl.params["outtmpl"]["default"] == parameters["outtmpl"]["default"]
        )


def test_yt_dlp_output_goes_to_python_logging(
    caplog: pytest.LogCaptureFixture,
) -> None:
    parameters = build_yt_dlp_parameters(DOWNLOAD_OPTIONS, MEDIA_SOURCE_SETTINGS)
    caplog.set_level(logging.DEBUG, logger="queued_media_downloader.yt_dlp")

    with YoutubeDL(parameters) as youtube_dl:
        youtube_dl.to_screen("[info] screen message")
        youtube_dl.report_warning("warning message")

    messages = {(record.levelno, record.getMessage()) for record in caplog.records}
    assert (logging.DEBUG, "[info] screen message") in messages
    assert (logging.WARNING, "warning message") in messages
