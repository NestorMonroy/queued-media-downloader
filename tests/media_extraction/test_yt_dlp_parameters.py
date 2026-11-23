import logging
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from queued_media_downloader.jobs import DownloadOptions
from queued_media_downloader.media_extraction import MediaSourceSettings
from queued_media_downloader.media_extraction.failure_classifier import (
    classify_failure,
)
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
    progress_interval_seconds=0.5,
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
        cache_directory=Path("cache"),
        ffmpeg_location=None,
        max_filename_length=150,
        progress_interval_seconds=0.5,
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


def test_audio_only_extracts_the_audio_without_reencoding() -> None:
    audio_only_options = replace(DOWNLOAD_OPTIONS, audio_only=True)

    parameters = build_yt_dlp_parameters(audio_only_options, MEDIA_SOURCE_SETTINGS)

    assert parameters["postprocessors"] == [
        {"key": "FFmpegExtractAudio", "preferredcodec": "best"}
    ]
    # Una subcarpeta propia: ningún nombre de un job de solo audio, ni el de su
    # descarga intermedia, puede coincidir con el de un video.
    assert parameters["paths"] == {"home": str(Path("downloads") / "audio")}


def test_media_with_video_has_no_postprocessors() -> None:
    parameters = build_yt_dlp_parameters(DOWNLOAD_OPTIONS, MEDIA_SOURCE_SETTINGS)

    assert "postprocessors" not in parameters


def test_yt_dlp_errors_reach_the_job_without_terminal_colors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # En Windows, run escribe en una terminal con color: yt-dlp coloreaba
    # "ERROR:" y el prefijo ya no se podía quitar del mensaje (T19).
    # El paquete exporta la clase YoutubeDL con el mismo nombre que su módulo.
    youtube_dl_module = sys.modules["yt_dlp.YoutubeDL"]
    monkeypatch.setattr(
        youtube_dl_module, "supports_terminal_sequences", lambda _stream: True
    )
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)
    parameters = build_yt_dlp_parameters(DOWNLOAD_OPTIONS, MEDIA_SOURCE_SETTINGS)

    with YoutubeDL(parameters) as youtube_dl, pytest.raises(DownloadError) as raised:
        youtube_dl.report_error("[youtube] abc: This video is unavailable")

    assert classify_failure(raised.value).failure_message == (
        "[youtube] abc: This video is unavailable"
    )
