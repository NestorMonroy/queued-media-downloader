from pathlib import Path, PureWindowsPath

import pytest
from yt_dlp import YoutubeDL

from queued_media_downloader.jobs import PlaylistContext
from queued_media_downloader.media_extraction.playlist_output_template import (
    build_playlist_output_template,
)

OUTPUT_TEMPLATE = "%(title)s [%(id)s].%(ext)s"
WINDOWS_FORBIDDEN_CHARACTERS = set('<>:"/\\|?*')


def playlist_context(
    playlist_title: str | None,
    playlist_index: int = 3,
    playlist_entry_count: int | None = 12,
) -> PlaylistContext:
    return PlaylistContext(
        playlist_id="PLxyz123",
        playlist_title=playlist_title,
        playlist_index=playlist_index,
        playlist_entry_count=playlist_entry_count,
    )


def template_for(context: PlaylistContext, max_filename_length: int = 150) -> str:
    return build_playlist_output_template(OUTPUT_TEMPLATE, context, max_filename_length)


def file_name_from(output_template: str) -> str:
    """Nombre que yt-dlp construye con la plantilla para un contenido de ejemplo."""
    with YoutubeDL({"outtmpl": output_template}) as youtube_dl:
        return str(
            youtube_dl.prepare_filename(
                {"title": "First song", "id": "abc123", "ext": "webm"}
            )
        )


@pytest.mark.parametrize(
    ("playlist_index", "playlist_entry_count", "expected_prefix"),
    [
        (3, 12, "03"),
        (3, 9, "3"),
        (42, 1200, "0042"),
        # Sin el número de entradas no hay relleno, como lazy_playlist de yt-dlp.
        (3, None, "3"),
    ],
)
def test_index_is_padded_to_the_digits_of_the_entry_count(
    playlist_index: int, playlist_entry_count: int | None, expected_prefix: str
) -> None:
    context = playlist_context("Mix", playlist_index, playlist_entry_count)

    assert template_for(context) == f"Mix/{expected_prefix} - {OUTPUT_TEMPLATE}"


def test_playlist_without_title_uses_its_id_as_folder() -> None:
    assert template_for(playlist_context(None)).startswith("PLxyz123/03 - ")


def test_folder_name_is_sanitized_like_a_yt_dlp_field() -> None:
    output_template = template_for(playlist_context('AC/DC: Best? <Hits> | "Live" *'))

    folder, file_name = PureWindowsPath(output_template).parts
    assert not WINDOWS_FORBIDDEN_CHARACTERS & set(folder)
    # yt-dlp los sustituye por sus equivalentes de ancho completo.
    assert folder == (
        "AC\u29f8DC\uff1a Best\uff1f \uff1cHits\uff1e \uff5c \uff02Live\uff02 \uff0a"
    )
    assert file_name == f"03 - {OUTPUT_TEMPLATE}"


def test_percent_in_the_title_reaches_the_folder_unchanged() -> None:
    output_template = template_for(playlist_context("100% Hits"))

    assert Path(file_name_from(output_template)) == Path(
        "100% Hits", "03 - First song [abc123].webm"
    )


def test_long_title_is_trimmed_to_the_file_name_length() -> None:
    output_template = template_for(
        playlist_context("Long " * 40), max_filename_length=20
    )

    folder = PureWindowsPath(output_template).parts[0]
    assert folder == "Long Long Long Long"
    assert len(folder) <= 20
