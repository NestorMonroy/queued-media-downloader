import io
import sys

import pytest
from yt_dlp.networking import Response
from yt_dlp.networking.exceptions import HTTPError, TransportError
from yt_dlp.utils import (
    DownloadError,
    ExtractorError,
    GeoRestrictedError,
    PostProcessingError,
    UnsupportedError,
)

from queued_media_downloader.jobs import FailureReason
from queued_media_downloader.media_extraction.failure_classifier import (
    classify_failure,
)


def http_error(status: int) -> HTTPError:
    """HTTPError real de yt-dlp con el código de estado indicado."""
    response = Response(
        fp=io.BytesIO(), url="https://example.com/media", headers={}, status=status
    )
    return HTTPError(response)


def wrapped_in_download_error(error: Exception) -> DownloadError:
    """Envuelve error como lo hace YoutubeDL.download al fallar."""
    try:
        raise error
    except Exception:
        return DownloadError(f"ERROR: {error}", sys.exc_info())


@pytest.mark.parametrize(
    ("error", "expected_reason"),
    [
        pytest.param(
            GeoRestrictedError("Not available in your country"),
            FailureReason.GEO_RESTRICTED,
            id="geo restricted",
        ),
        pytest.param(
            UnsupportedError("https://example.com/page"),
            FailureReason.UNSUPPORTED_URL,
            id="unsupported url",
        ),
        pytest.param(
            TransportError("timed out"), FailureReason.NETWORK, id="transport error"
        ),
        pytest.param(
            ExtractorError("Unable to download", cause=TransportError("reset")),
            FailureReason.NETWORK,
            id="extractor error caused by the network",
        ),
        pytest.param(http_error(503), FailureReason.NETWORK, id="http 503"),
        pytest.param(http_error(404), FailureReason.UNAVAILABLE, id="http 404"),
        pytest.param(
            ExtractorError("Unable to download", cause=http_error(410)),
            FailureReason.UNAVAILABLE,
            id="extractor error caused by http 410",
        ),
        pytest.param(
            ExtractorError("Private video", expected=True),
            FailureReason.UNAVAILABLE,
            id="expected extractor error",
        ),
        pytest.param(
            ExtractorError("Unable to extract title"),
            FailureReason.EXTRACTOR_OUTDATED,
            id="unexpected extractor error",
        ),
        pytest.param(
            PostProcessingError("Conversion failed"),
            FailureReason.POSTPROCESSING,
            id="postprocessing error",
        ),
        pytest.param(
            PermissionError("Access is denied"),
            FailureReason.FILESYSTEM,
            id="file system error",
        ),
        pytest.param(
            ConnectionResetError("reset"),
            FailureReason.NETWORK,
            id="connection error from the socket",
        ),
        pytest.param(ValueError("surprise"), FailureReason.UNKNOWN, id="anything else"),
    ],
)
def test_error_is_classified_with_or_without_download_error_wrapper(
    error: Exception, expected_reason: FailureReason
) -> None:
    assert classify_failure(error).failure_reason is expected_reason
    assert (
        classify_failure(wrapped_in_download_error(error)).failure_reason
        is expected_reason
    )


def test_message_drops_the_error_prefix_of_yt_dlp() -> None:
    job_failed = classify_failure(wrapped_in_download_error(http_error(404)))

    assert job_failed.failure_message == "HTTP Error 404: Not Found"


def test_outdated_extractor_message_suggests_updating_the_pinned_version() -> None:
    job_failed = classify_failure(ExtractorError("Unable to extract title"))

    assert job_failed.failure_message.startswith("Unable to extract title.")
    assert "yt-dlp" in job_failed.failure_message
    assert "please report this issue" not in job_failed.failure_message
