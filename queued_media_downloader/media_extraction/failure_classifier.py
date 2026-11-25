"""Traduce las excepciones de yt-dlp a la clasificación de dominio FailureReason.

La clasificación se decide con la causa más interna (YoutubeDL.download envuelve
el error original en DownloadError) y el mensaje con el texto más externo, que
es el que conserva el contexto (extractor, id del contenido).
"""

import re

from yt_dlp.networking.exceptions import HTTPError, RequestError
from yt_dlp.utils import (
    DownloadError,
    ExtractorError,
    GeoRestrictedError,
    PostProcessingError,
    UnsupportedError,
    bug_reports_message,
)

from queued_media_downloader.jobs import FailureReason, JobFailed

# Códigos HTTP que indican que el contenido ya no existe, no un fallo de red.
UNAVAILABLE_HTTP_STATUSES = frozenset({404, 410})
OUTDATED_EXTRACTOR_HINT = (
    "The site probably changed; the pinned yt-dlp version may need an update."
)
YT_DLP_ERROR_PREFIX = "ERROR: "
# Texto con el que yt-dlp avisa de que el formato pedido no se ofrece
# (YoutubeDL.process_video_result, versión fijada 2026.10.26).
FORMAT_UNAVAILABLE_MESSAGE = "Requested format is not available"
# yt-dlp añade la causa al final del mensaje: " (caused by <HTTPError 404: ...>)".
CAUSE_SUFFIX = re.compile(r" \(caused by .*\)$")


def classify_failure(error: Exception) -> JobFailed:
    """Devuelve el job event que describe el fallo de un job."""
    failure_reason = _failure_reason_of(_original_error(error))
    failure_message = _readable_message(error)
    if failure_reason is FailureReason.EXTRACTOR_OUTDATED:
        failure_message = f"{failure_message}. {OUTDATED_EXTRACTOR_HINT}"
    return JobFailed(failure_reason=failure_reason, failure_message=failure_message)


def is_format_unavailable(error: Exception) -> bool:
    """Indica si el error es que el sitio ya no ofrece el formato pedido."""
    original_error = _original_error(error)
    return isinstance(original_error, ExtractorError) and (
        FORMAT_UNAVAILABLE_MESSAGE in original_error.orig_msg
    )


def _original_error(error: Exception) -> Exception:
    """Quita los envoltorios DownloadError, si los hay.

    Un error que yt-dlp informa mientras se atiende otro guarda ese otro como
    causa, así que puede haber un DownloadError dentro de otro.
    """
    while isinstance(error, DownloadError) and isinstance(error.exc_info, tuple):
        original = error.exc_info[1]
        if not isinstance(original, Exception) or original is error:
            break
        error = original
    return error


def _failure_reason_of(error: Exception) -> FailureReason:
    """Clasifica el error ya sin envoltorio."""
    if isinstance(error, GeoRestrictedError):
        return FailureReason.GEO_RESTRICTED
    if isinstance(error, UnsupportedError):
        return FailureReason.UNSUPPORTED_URL
    if isinstance(error, ExtractorError):
        return _failure_reason_of_extractor_error(error)
    if isinstance(error, HTTPError | RequestError | ConnectionError | TimeoutError):
        return _failure_reason_of_network_error(error)
    if isinstance(error, PostProcessingError):
        return FailureReason.POSTPROCESSING
    if isinstance(error, OSError):
        return FailureReason.FILESYSTEM
    return FailureReason.UNKNOWN


def _failure_reason_of_extractor_error(error: ExtractorError) -> FailureReason:
    """Un fallo de red disfrazado, un contenido no disponible o un extractor roto."""
    if isinstance(error.cause, HTTPError | RequestError):
        return _failure_reason_of_network_error(error.cause)
    if error.expected:
        return FailureReason.UNAVAILABLE
    # yt-dlp marca como inesperado lo que considera un fallo propio: casi
    # siempre, que el sitio cambió y el extractor de la versión fijada no lo sabe.
    return FailureReason.EXTRACTOR_OUTDATED


def _failure_reason_of_network_error(error: Exception) -> FailureReason:
    """Distingue un contenido que ya no existe de un fallo de la conexión."""
    if isinstance(error, HTTPError) and error.status in UNAVAILABLE_HTTP_STATUSES:
        return FailureReason.UNAVAILABLE
    return FailureReason.NETWORK


def _readable_message(error: Exception) -> str:
    """Mensaje para el usuario, sin el prefijo, la causa ni el aviso de yt-dlp."""
    if isinstance(error, ExtractorError):
        message = error.orig_msg
    else:
        message = str(error).removeprefix(YT_DLP_ERROR_PREFIX)
    message = message.replace(bug_reports_message(), "")
    return CAUSE_SUFFIX.sub("", message).strip()
