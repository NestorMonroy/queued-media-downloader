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
    """Servidor HTTP local con videos y una página con dos; devuelve su URL base.

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
    request_handler = functools.partial(
        QuietRequestHandler, directory=str(served_directory)
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), request_handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
