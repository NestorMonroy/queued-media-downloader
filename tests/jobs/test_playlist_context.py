import pytest

from queued_media_downloader.jobs import PlaylistContext


def test_playlist_context_keeps_its_values() -> None:
    playlist_context = PlaylistContext(
        playlist_id="PL123",
        playlist_title="Favorites",
        playlist_index=3,
        playlist_entry_count=10,
    )

    assert playlist_context.playlist_index == 3
    assert playlist_context.playlist_entry_count == 10


def test_entry_count_and_title_may_be_unknown() -> None:
    # La expansión recorre las entradas de forma perezosa: al crear los
    # primeros hijos aún no sabe cuántas hay (UC-04, paso 2).
    playlist_context = PlaylistContext(
        playlist_id="PL123",
        playlist_title=None,
        playlist_index=1,
        playlist_entry_count=None,
    )

    assert playlist_context.playlist_entry_count is None


@pytest.mark.parametrize(
    ("playlist_index", "playlist_entry_count"),
    [(0, None), (-1, 10), (11, 10)],
    ids=["index zero", "negative index", "index beyond the count"],
)
def test_invalid_position_is_rejected(
    playlist_index: int, playlist_entry_count: int | None
) -> None:
    with pytest.raises(ValueError, match="playlist_index"):
        PlaylistContext(
            playlist_id="PL123",
            playlist_title="Favorites",
            playlist_index=playlist_index,
            playlist_entry_count=playlist_entry_count,
        )


def test_playlist_id_is_required() -> None:
    with pytest.raises(ValueError, match="playlist_id"):
        PlaylistContext(
            playlist_id="",
            playlist_title="Favorites",
            playlist_index=1,
            playlist_entry_count=None,
        )
