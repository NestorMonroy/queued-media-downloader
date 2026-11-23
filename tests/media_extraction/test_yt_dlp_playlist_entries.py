from collections.abc import Iterator
from typing import Any

import pytest
from yt_dlp import YoutubeDL

from queued_media_downloader.jobs import JobKind, MediaKey, PlaylistEntry
from queued_media_downloader.media_extraction.yt_dlp_playlist_entries import (
    playlist_entry_from,
)

# Entradas planas tal como las devuelve el extractor de YouTube con
# process=False, sin los campos que no se usan.
YOUTUBE_VIDEO_ENTRY: dict[str, Any] = {
    "_type": "url",
    "ie_key": "Youtube",
    "id": "jNQXAC9IVRw",
    "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "title": "Me at the zoo",
    "availability": None,
}


@pytest.fixture
def youtube_dl() -> Iterator[YoutubeDL]:
    """YoutubeDL sin red: solo se consultan sus extractores."""
    with YoutubeDL({"quiet": True}) as youtube_dl:
        yield youtube_dl


def test_youtube_video_becomes_a_download_with_its_media_key(
    youtube_dl: YoutubeDL,
) -> None:
    assert playlist_entry_from(youtube_dl, 4, YOUTUBE_VIDEO_ENTRY) == PlaylistEntry(
        url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
        playlist_index=4,
        kind=JobKind.DOWNLOAD,
        title="Me at the zoo",
        media_key=MediaKey(extractor_key="Youtube", media_id="jNQXAC9IVRw"),
        is_available=True,
    )


@pytest.mark.parametrize(
    "unavailable_fields",
    [
        {"title": "[Private video]"},
        {"title": "[Deleted video]"},
        {"availability": "private"},
        {"availability": "needs_auth"},
        {"availability": "premium_only"},
        {"availability": "subscriber_only"},
    ],
    ids=repr,
)
def test_private_deleted_or_restricted_entries_are_unavailable(
    youtube_dl: YoutubeDL, unavailable_fields: dict[str, Any]
) -> None:
    entry = {**YOUTUBE_VIDEO_ENTRY, **unavailable_fields}

    playlist_entry = playlist_entry_from(youtube_dl, 1, entry)

    assert playlist_entry is not None
    assert not playlist_entry.is_available


def test_unlisted_entry_is_available(youtube_dl: YoutubeDL) -> None:
    entry = {**YOUTUBE_VIDEO_ENTRY, "availability": "unlisted"}

    playlist_entry = playlist_entry_from(youtube_dl, 1, entry)

    assert playlist_entry is not None
    assert playlist_entry.is_available


@pytest.mark.parametrize(
    "entry",
    [
        {
            "_type": "url",
            "ie_key": "YoutubeTab",
            "id": "UC123",
            "url": "https://www.youtube.com/channel/UC123/videos",
            "title": "Videos",
        },
        {
            "_type": "playlist",
            "id": "PL123",
            "url": "https://www.youtube.com/playlist?list=PL123",
            "title": "Nested",
        },
        {
            "_type": "url_transparent",
            "url": "https://media.example/feed-item",
            "title": "Unknown extractor",
        },
        {
            "_type": "url",
            "ie_key": "Youtube",
            "url": "https://www.youtube.com/watch?v=noid",
            "title": "Without id",
        },
    ],
    ids=["channel tab", "nested playlist", "unknown extractor", "video without id"],
)
def test_entries_that_may_not_be_a_single_media_become_expansions(
    youtube_dl: YoutubeDL, entry: dict[str, Any]
) -> None:
    # Una expansión hija averigua qué hay detrás y, si es un contenido, pasa a
    # descarga con su media key, que la regla de duplicados necesita.
    playlist_entry = playlist_entry_from(youtube_dl, 1, entry)

    assert playlist_entry is not None
    assert playlist_entry.kind is JobKind.EXPANSION
    assert playlist_entry.media_key is None


def test_entry_without_any_url_cannot_become_a_job(youtube_dl: YoutubeDL) -> None:
    entry = {"_type": "video", "id": "embedded-1", "title": "Embedded video"}

    assert playlist_entry_from(youtube_dl, 1, entry) is None
