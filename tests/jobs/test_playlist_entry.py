import pytest

from queued_media_downloader.jobs import JobKind, MediaKey, PlaylistEntry


def playlist_entry(url: str, playlist_index: int) -> PlaylistEntry:
    """Entrada de playlist con los valores indicados y el resto por defecto."""
    return PlaylistEntry(
        url=url,
        playlist_index=playlist_index,
        kind=JobKind.EXPANSION,
        title=None,
        media_key=None,
        is_available=True,
    )


def test_entry_needs_a_url() -> None:
    with pytest.raises(ValueError, match="url"):
        playlist_entry("", 1)


def test_entry_index_starts_at_one() -> None:
    with pytest.raises(ValueError, match="playlist_index"):
        playlist_entry("https://media.example/watch?v=a", 0)


def test_download_entry_needs_its_media_key() -> None:
    with pytest.raises(ValueError, match="media_key"):
        PlaylistEntry(
            url="https://media.example/watch?v=a",
            playlist_index=1,
            kind=JobKind.DOWNLOAD,
            title=None,
            media_key=None,
            is_available=True,
        )


def test_download_entry_with_its_media_key_is_valid() -> None:
    entry = PlaylistEntry(
        url="https://media.example/watch?v=a",
        playlist_index=1,
        kind=JobKind.DOWNLOAD,
        title="A",
        media_key=MediaKey(extractor_key="Example", media_id="a"),
        is_available=True,
    )

    assert entry.media_key == MediaKey(extractor_key="Example", media_id="a")
