"""Convierte las entradas de una playlist de yt-dlp en PlaylistEntry (UC-04).

Con process=False, yt-dlp enumera las entradas sin resolverlas: cada una trae
como mucho su URL, su extractor, su id, su título y su disponibilidad.
"""

from collections.abc import Iterator, Mapping
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import PlaylistEntries

from queued_media_downloader.jobs import JobKind, MediaKey, PlaylistEntry

# Valores de availability de yt-dlp con los que la entrada no se puede
# descargar sin una cuenta o un permiso que el proyecto no tiene (A3).
UNAVAILABLE_AVAILABILITIES = frozenset(
    {"private", "needs_auth", "premium_only", "subscriber_only"}
)
# Títulos con los que YouTube marca en una playlist un video privado o borrado.
UNAVAILABLE_TITLES = frozenset({"[Private video]", "[Deleted video]"})
URL_RESULT_TYPES = frozenset({"url", "url_transparent"})


def iterate_playlist_entries(
    youtube_dl: YoutubeDL, playlist_result: Mapping[str, Any]
) -> Iterator[tuple[int, Any]]:
    """Recorre las entradas de forma perezosa, con su posición desde 1.

    Usa el mismo mecanismo que yt-dlp, que acepta listas, generadores y listas
    paginadas sin cargarlas enteras en memoria.
    """
    yield from PlaylistEntries(youtube_dl, playlist_result).get_requested_items()


def playlist_entry_from(
    youtube_dl: YoutubeDL, playlist_index: int, entry: Any
) -> PlaylistEntry | None:
    """Entrada de playlist del proyecto; None si no tiene una URL propia.

    Solo es DOWNLOAD una entrada que su extractor declara como un solo
    contenido y que trae su id: el job hijo necesita la media key para la regla
    de duplicados. Cualquier otra es EXPANSION y se resuelve al ejecutarla.
    """
    if not isinstance(entry, Mapping):
        return None
    url = entry.get("url") or entry.get("webpage_url")
    if not url:
        return None
    media_key = _single_media_key(youtube_dl, entry, url)
    return PlaylistEntry(
        url=url,
        playlist_index=playlist_index,
        kind=JobKind.DOWNLOAD if media_key else JobKind.EXPANSION,
        title=entry.get("title"),
        media_key=media_key,
        is_available=_is_available(entry),
    )


def _single_media_key(
    youtube_dl: YoutubeDL, entry: Mapping[str, Any], url: str
) -> MediaKey | None:
    """Media key si el extractor declara que la URL es un solo contenido."""
    extractor_key = entry.get("ie_key")
    media_id = entry.get("id")
    if entry.get("_type") not in URL_RESULT_TYPES or not extractor_key or not media_id:
        return None
    extractor = youtube_dl.get_info_extractor(extractor_key)
    if type(extractor).is_single_video(url) is not True:
        return None
    return MediaKey(extractor_key=extractor_key, media_id=str(media_id))


def _is_available(entry: Mapping[str, Any]) -> bool:
    """Una entrada privada, borrada o que pide una cuenta no se puede descargar."""
    return (
        entry.get("availability") not in UNAVAILABLE_AVAILABILITIES
        and entry.get("title") not in UNAVAILABLE_TITLES
    )
