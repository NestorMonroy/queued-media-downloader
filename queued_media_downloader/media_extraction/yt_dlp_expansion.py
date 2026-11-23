"""Expansión de una URL con yt-dlp: un contenido o una playlist (UC-03, UC-04)."""

import logging
from collections.abc import Mapping
from typing import Any

from yt_dlp import YoutubeDL

from queued_media_downloader.jobs import (
    FailureReason,
    JobCompleted,
    JobFailed,
    MediaKey,
    PlaylistEntriesFound,
    PlaylistEntry,
    SingleMediaFound,
)
from queued_media_downloader.media_extraction.media_source import Publish
from queued_media_downloader.media_extraction.yt_dlp_playlist_entries import (
    URL_RESULT_TYPES,
    iterate_playlist_entries,
    playlist_entry_from,
)

logger = logging.getLogger(__name__)

# Tipos de resultado de yt-dlp que son un solo contenido. Un multi_video (un
# contenido partido en varios videos) también lo es (UC-04 A4).
SINGLE_MEDIA_RESULT_TYPES = frozenset({"video", "multi_video"})
# Saltos que se siguen cuando una URL solo apunta a otra (por ejemplo, una
# redirección); más saltos indican un bucle.
MAX_URL_REDIRECTS = 5


def expand_url(
    youtube_dl: YoutubeDL, url: str, publish: Publish, playlist_batch_size: int
) -> None:
    """Averigua qué hay detrás de url y lo publica, sin descargar nada.

    Un contenido publica SingleMediaFound. Una playlist publica sus entradas
    por lotes de playlist_batch_size y termina con JobCompleted; los lotes ya
    publicados se conservan aunque la expansión falle después (UC-04 A6).
    """
    result = _extract_following_redirects(youtube_dl, url)
    result_type = result.get("_type", "video")
    if result_type in SINGLE_MEDIA_RESULT_TYPES:
        publish(_single_media_found_from(result))
    elif result_type == "playlist":
        _publish_playlist(youtube_dl, url, result, publish, playlist_batch_size)
    else:
        publish(
            JobFailed(
                failure_reason=FailureReason.UNSUPPORTED_URL,
                failure_message=f"Results of type {result_type} are not supported",
            )
        )


def _extract_following_redirects(youtube_dl: YoutubeDL, url: str) -> dict[str, Any]:
    """Extrae sin procesar y sigue los resultados que solo apuntan a otra URL."""
    extractor_key = None
    for _ in range(MAX_URL_REDIRECTS):
        # process=False no resuelve formatos ni recorre playlists: solo
        # identifica qué hay detrás de la URL.
        result: dict[str, Any] = youtube_dl.extract_info(
            url, download=False, ie_key=extractor_key, process=False
        )
        if result.get("_type") not in URL_RESULT_TYPES:
            return result
        url, extractor_key = result["url"], result.get("ie_key")
    return result


def _single_media_found_from(result: Mapping[str, Any]) -> SingleMediaFound:
    """Toma del resultado de yt-dlp solo la identidad y el título del contenido."""
    media_id = str(result["id"])
    return SingleMediaFound(
        media_key=MediaKey(extractor_key=result["extractor_key"], media_id=media_id),
        title=result.get("title") or media_id,
    )


def _publish_playlist(
    youtube_dl: YoutubeDL,
    url: str,
    playlist_result: Mapping[str, Any],
    publish: Publish,
    playlist_batch_size: int,
) -> None:
    """Publica las entradas por lotes sin cargar la playlist entera en memoria."""
    playlist_id = str(playlist_result.get("id") or url)
    playlist_title = playlist_result.get("title")
    batch: list[PlaylistEntry] = []
    entry_count = usable_entry_count = 0

    def publish_batch() -> None:
        publish(
            PlaylistEntriesFound(
                playlist_id=playlist_id,
                playlist_title=playlist_title,
                playlist_entries=tuple(batch),
            )
        )
        batch.clear()

    for playlist_index, entry in iterate_playlist_entries(youtube_dl, playlist_result):
        entry_count += 1
        playlist_entry = playlist_entry_from(youtube_dl, playlist_index, entry)
        if playlist_entry is None:
            logger.warning("Playlist entry %s has no URL of its own", playlist_index)
            continue
        usable_entry_count += 1
        batch.append(playlist_entry)
        if len(batch) == playlist_batch_size:
            publish_batch()
    if batch:
        publish_batch()
    if entry_count and not usable_entry_count:
        publish(
            JobFailed(
                failure_reason=FailureReason.UNSUPPORTED_URL,
                failure_message=(
                    f"None of the {entry_count} playlist entries has a URL of its own"
                ),
            )
        )
        return
    publish(JobCompleted(output_path=None))
