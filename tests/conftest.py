"""Fixtures compartidas por varias carpetas de pruebas."""

import functools
import threading
from collections.abc import Iterator
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

SAMPLE_MEDIA_NAME = "sample.mp4"
SAMPLE_MEDIA_CONTENT = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 64
# Página con dos videos: yt-dlp la interpreta como una playlist.
TWO_VIDEOS_PAGE_NAME = "two-videos.html"
# Feed RSS: el extractor genérico lo devuelve como una playlist de entradas
# url_transparent, con la misma forma que las de YouTube.
FEED_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
    "<title>{title}</title><link>{base}/</link><description>-</description>"
    "{items}</channel></rss>"
)
FEED_ITEM_TEMPLATE = "<item><title>{title}</title><link>{base}/{name}</link></item>"
# Página que redirige a sample.mp4: yt-dlp la devuelve como un resultado url.
REDIRECT_PAGE = (
    '<html><head><meta http-equiv="refresh" content="0; url=sample.mp4">'
    "<title>Redirect</title></head><body></body></html>"
)
TWO_VIDEOS_PAGE = (
    "<html><head><title>Two videos</title></head><body>"
    f'<video src="{SAMPLE_MEDIA_NAME}"></video><video src="other.mp4"></video>'
    "</body></html>"
)


class QuietRequestHandler(SimpleHTTPRequestHandler):
    """Sirve archivos sin escribir cada petición en la salida de las pruebas."""

    def log_message(self, format: str, *args: Any) -> None:
        """No registra nada."""


@pytest.fixture
def local_media_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[str]:
    """Servidor HTTP local con videos, playlists y redirecciones; devuelve su URL base.

    Las pruebas descargan sin internet (diseño, Parte 2, §5). Las direcciones
    locales se excluyen del proxy del entorno, si lo hay.
    """
    served_directory = tmp_path / "served"
    served_directory.mkdir()
    (served_directory / SAMPLE_MEDIA_NAME).write_bytes(SAMPLE_MEDIA_CONTENT)
    (served_directory / "other.mp4").write_bytes(SAMPLE_MEDIA_CONTENT)
    (served_directory / TWO_VIDEOS_PAGE_NAME).write_text(
        TWO_VIDEOS_PAGE, encoding="utf-8"
    )
    for variable in ("NO_PROXY", "no_proxy"):
        monkeypatch.setenv(variable, "127.0.0.1,localhost")
    (served_directory / "redirect.html").write_text(REDIRECT_PAGE, encoding="utf-8")
    request_handler = functools.partial(
        QuietRequestHandler, directory=str(served_directory)
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), request_handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    write_feed(
        served_directory / "feed.xml",
        base_url,
        "Local feed",
        [
            ("Video A", SAMPLE_MEDIA_NAME),
            ("Video B", "other.mp4"),
            ("Nested", "nested.xml"),
        ],
    )
    write_feed(
        served_directory / "nested.xml",
        base_url,
        "Nested feed",
        [("Video B again", "other.mp4")],
    )
    try:
        yield base_url
    finally:
        server.shutdown()
        server.server_close()


def write_feed(
    path: Path, base_url: str, title: str, items: list[tuple[str, str]]
) -> None:
    """Escribe un feed RSS con un item por (título, archivo servido)."""
    feed_items = "".join(
        FEED_ITEM_TEMPLATE.format(title=item_title, base=base_url, name=name)
        for item_title, name in items
    )
    path.write_text(
        FEED_TEMPLATE.format(title=title, base=base_url, items=feed_items),
        encoding="utf-8",
    )
