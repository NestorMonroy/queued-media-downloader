"""Fixtures compartidas por varias carpetas de pruebas."""

import functools
import io
import threading
import time
from collections.abc import Iterator
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from tests.real_environment_guard import (
    RealDataSnapshot,
    isolate_environment,
    real_locations,
)

SAMPLE_MEDIA_NAME = "sample.mp4"
SAMPLE_MEDIA_CONTENT = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 64
# Contenido que el servidor envía despacio, para interrumpir una descarga a
# medias (plan de E2, §5.1): unos 3 s en total.
SLOW_MEDIA_NAME = "slow.mp4"
SLOW_MEDIA_CONTENT = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 3072
SLOW_CHUNK_SIZE = 16 * 1024
SLOW_CHUNK_DELAY_SECONDS = 0.06
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
    """Sirve archivos, admite Range y anota cada petición con su cabecera Range.

    SimpleHTTPRequestHandler ignora Range; sin él, yt-dlp no podría continuar
    un .part (UC-06, paso 6).
    """

    def __init__(
        self, *args: Any, media_requests: list[tuple[str, str | None]], **kwargs: Any
    ) -> None:
        """Anota en media_requests (ruta, cabecera Range) de cada petición."""
        self._media_requests = media_requests
        super().__init__(*args, **kwargs)

    def send_head(self) -> Any:
        """Responde 206 con el resto del archivo si la petición lleva Range."""
        return _slowed_down_if_requested(self.path, self._send_head())

    def _send_head(self) -> Any:
        range_header = self.headers.get("Range")
        self._media_requests.append((self.path, range_header))
        if range_header is None:
            return super().send_head()
        content = Path(self.translate_path(self.path)).read_bytes()
        first_byte = int(range_header.removeprefix("bytes=").split("-")[0])
        self.send_response(HTTPStatus.PARTIAL_CONTENT)
        self.send_header("Content-Type", self.guess_type(self.path))
        self.send_header(
            "Content-Range", f"bytes {first_byte}-{len(content) - 1}/{len(content)}"
        )
        self.send_header("Content-Length", str(len(content) - first_byte))
        self.end_headers()
        return io.BytesIO(content[first_byte:])

    def log_message(self, format: str, *args: Any) -> None:
        """No escribe cada petición en la salida de las pruebas."""


class SlowReader:
    """Entrega el cuerpo de la respuesta por bloques, con una pausa entre ellos."""

    def __init__(self, source: Any) -> None:
        """Lee de source, el archivo que devolvió send_head."""
        self._source = source

    def read(self, size: int = -1) -> bytes:
        """Un bloque de SLOW_CHUNK_SIZE como máximo, tras una pausa."""
        time.sleep(SLOW_CHUNK_DELAY_SECONDS)
        limit = SLOW_CHUNK_SIZE if size < 0 else min(size, SLOW_CHUNK_SIZE)
        return bytes(self._source.read(limit))

    def close(self) -> None:
        """Cierra el archivo de origen."""
        self._source.close()


_REAL_DATA_BEFORE: dict[str, RealDataSnapshot] = {}


def pytest_sessionstart() -> None:
    """Toma la huella de los datos reales y exige que no haya config.toml."""
    locations = real_locations()
    if locations["config"].exists():
        # Las pruebas que lanzan el programa en otro proceso (Ctrl+C real)
        # leerían ese archivo: no se puede aislar de él.
        message = (
            f"{locations['config']} exists; run the tests from a checkout "
            "without a config.toml"
        )
        raise pytest.UsageError(message)
    _REAL_DATA_BEFORE["snapshot"] = RealDataSnapshot.take(locations)


def pytest_sessionfinish(session: pytest.Session) -> None:
    """Hace fallar la sesión si algún dato real cambió durante las pruebas."""
    before = _REAL_DATA_BEFORE.get("snapshot")
    if before is None:
        return
    differences = before.differences(RealDataSnapshot.take(real_locations()))
    if differences:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        lines = "\n".join(f"  {difference}" for difference in differences)
        if reporter is not None:
            reporter.write_line(
                f"REAL USER DATA CHANGED DURING THE TESTS:\n{lines}", red=True
            )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Toda prueba usa estado, descargas y config.toml propios (auditoría §5)."""
    return isolate_environment(tmp_path, monkeypatch)


def _slowed_down_if_requested(path: str, body: Any) -> Any:
    """Envuelve el cuerpo de SLOW_MEDIA_NAME para enviarlo despacio."""
    if body is None or not path.endswith(SLOW_MEDIA_NAME):
        return body
    return SlowReader(body)


@pytest.fixture
def media_requests() -> list[tuple[str, str | None]]:
    """Peticiones que recibió el servidor local: (ruta, cabecera Range), en orden."""
    return []


@pytest.fixture
def local_media_server(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    media_requests: list[tuple[str, str | None]],
) -> Iterator[str]:
    """Servidor HTTP local con videos, playlists y redirecciones; devuelve su URL base.

    Las pruebas descargan sin internet (diseño, Parte 2, §5). Las direcciones
    locales se excluyen del proxy del entorno, si lo hay.
    """
    served_directory = tmp_path / "served"
    served_directory.mkdir()
    (served_directory / SAMPLE_MEDIA_NAME).write_bytes(SAMPLE_MEDIA_CONTENT)
    (served_directory / "other.mp4").write_bytes(SAMPLE_MEDIA_CONTENT)
    (served_directory / SLOW_MEDIA_NAME).write_bytes(SLOW_MEDIA_CONTENT)
    (served_directory / TWO_VIDEOS_PAGE_NAME).write_text(
        TWO_VIDEOS_PAGE, encoding="utf-8"
    )
    for variable in ("NO_PROXY", "no_proxy"):
        monkeypatch.setenv(variable, "127.0.0.1,localhost")
    (served_directory / "redirect.html").write_text(REDIRECT_PAGE, encoding="utf-8")
    request_handler = functools.partial(
        QuietRequestHandler,
        directory=str(served_directory),
        media_requests=media_requests,
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
