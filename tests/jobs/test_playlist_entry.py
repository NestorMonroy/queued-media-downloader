import pytest

from queued_media_downloader.jobs import JobKind, PlaylistEntry


def playlist_entry(url: str, playlist_index: int) -> PlaylistEntry:
    """Entrada de playlist con los valores indicados y el resto por defecto."""
    return PlaylistEntry(
        url=url,
        playlist_index=playlist_index,
        kind=JobKind.DOWNLOAD,
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
