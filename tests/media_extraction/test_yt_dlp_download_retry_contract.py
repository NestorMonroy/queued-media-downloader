"""Contrato con yt-dlp: cómo informa el downloader HTTP que agotó sus reintentos.

Tras el último reintento, yt-dlp lanza un DownloadError fuera de cualquier
bloque except: el error de red original se pierde y solo queda el texto
"[download] Got error: ...". En la validación en Windows, un timeout de conexión
quedó como UNKNOWN en lugar de NETWORK (T42-D7).
"""

from yt_dlp import YoutubeDL
from yt_dlp.downloader.http import HttpFD
from yt_dlp.networking.exceptions import TransportError
from yt_dlp.utils import DownloadError

from queued_media_downloader.jobs import FailureReason
from queued_media_downloader.media_extraction.failure_classifier import (
    classify_failure,
)


def error_after_download_retries(error: Exception) -> DownloadError:
    """Error real de yt-dlp cuando el downloader HTTP agota los reintentos."""
    with YoutubeDL({"quiet": True, "no_warnings": True}) as youtube_dl:
        downloader = HttpFD(youtube_dl, {"retries": 1})
        try:
            downloader.report_retry(error, count=2, retries=1)
        except DownloadError as download_error:
            return download_error
    raise AssertionError("yt-dlp no lanzó DownloadError")


def test_a_connection_timeout_after_the_retries_is_a_network_failure() -> None:
    error = error_after_download_retries(
        TransportError("Connection to rr2.googlevideo.com timed out.")
    )

    job_failed = classify_failure(error)

    assert job_failed.failure_reason is FailureReason.NETWORK
    assert job_failed.failure_message.startswith("[download] Got error: Connection")
