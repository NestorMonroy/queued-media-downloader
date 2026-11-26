"""Experimentos de cualificación de las decisiones de requisitos (D-3, D-12; UC-23).

Cada experimento responde una pregunta concreta, con entradas controladas, en
un directorio temporal propio, sin red externa y sin tocar la cola, el estado,
las descargas ni la configuración reales:

- retries: ¿basta pasar retries y fragment_retries a yt-dlp para que una
  descarga sobreviva a respuestas 503 transitorias? (R-24, D-3). Servidor HTTP
  local en 127.0.0.1 que falla las primeras peticiones de descarga.
- sqlite-backup: ¿la API de copia de seguridad de SQLite produce una copia
  íntegra y transaccionalmente coherente mientras otro hilo escribe en modo
  WAL? (UC-23).
- cause-chain: en los cinco caminos de error de almacenamiento de yt-dlp
  (catálogo de condiciones, §3.2), ¿qué códigos recupera un recorrido completo
  de la cadena (exc_info, __cause__, __context__) frente al clasificador
  actual? (R-28, D-12).

Uso, desde la raíz del repositorio:

    uv run python scripts/experiments/requirements_qualification.py [--output RUTA]

Escribe un JSON con la versión de yt-dlp, la plataforma y el resultado de cada
experimento. No es código de producción: no lo importa el paquete ni lo
ejecuta pytest.
"""

import argparse
import contextlib
import errno
import http.server
import json
import os
import platform
import sqlite3
import sys
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yt_dlp
from yt_dlp import YoutubeDL
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessorError
from yt_dlp.utils import DownloadError, UnavailableVideoError

from queued_media_downloader.jobs import DownloadOptions
from queued_media_downloader.media_extraction import MediaSourceSettings
from queued_media_downloader.media_extraction.failure_classifier import (
    classify_failure,
)
from queued_media_downloader.media_extraction.yt_dlp_parameters import (
    build_yt_dlp_parameters,
)

MEDIA_BYTES = b"\0" * 262_144
FAILED_DOWNLOAD_REQUESTS = 2


class FlakyMediaHandler(http.server.BaseHTTPRequestHandler):
    """Sirve un medio; falla con 503 las primeras peticiones de descarga.

    La primera petición es la de extracción (el extractor genérico lee las
    cabeceras) y siempre responde bien; las FAILED_DOWNLOAD_REQUESTS siguientes
    responden 503; después, todas responden bien.
    """

    requests_seen = 0
    lock = threading.Lock()

    def do_GET(self) -> None:
        """Responde según el número de petición."""
        with FlakyMediaHandler.lock:
            FlakyMediaHandler.requests_seen += 1
            number = FlakyMediaHandler.requests_seen
        if 2 <= number <= 1 + FAILED_DOWNLOAD_REQUESTS:
            self.send_response(503)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(len(MEDIA_BYTES)))
        self.end_headers()
        self.wfile.write(MEDIA_BYTES)

    def log_message(self, format: str, *args: Any) -> None:
        """Silencia el registro de peticiones."""


@contextlib.contextmanager
def flaky_media_server() -> Iterator[str]:
    """Arranca el servidor local y devuelve la URL del medio."""
    FlakyMediaHandler.requests_seen = 0
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FlakyMediaHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/media.mp4"
    finally:
        server.shutdown()
        server.server_close()


def download_with(work: Path, extra: dict[str, Any]) -> dict[str, Any]:
    """Descarga el medio con los parámetros del producto más extra."""
    options = DownloadOptions(
        format_selector="b",
        download_directory=work / "downloads",
        output_template="%(title)s.%(ext)s",
        audio_only=False,
    )
    settings = MediaSourceSettings(
        cache_directory=work / "state" / "yt-dlp-cache",
        output_claims_directory=work / "state" / "output-claims",
        ffmpeg_location=None,
        max_filename_length=150,
        progress_interval_seconds=0.5,
    )
    parameters = {
        **build_yt_dlp_parameters(options, settings, partial_directory=work / "part"),
        **extra,
    }
    with flaky_media_server() as url:
        try:
            with YoutubeDL(parameters) as ydl:
                ydl.download([url])
        except DownloadError as error:
            return {
                "completed": False,
                "failure_reason": classify_failure(error).failure_reason.name,
                "requests": FlakyMediaHandler.requests_seen,
            }
    files = [path.name for path in (work / "downloads").glob("*")]
    return {"completed": bool(files), "requests": FlakyMediaHandler.requests_seen}


def retries_experiment() -> dict[str, Any]:
    """R-24: parámetros del producto frente a los mismos con reintentos."""
    results: dict[str, Any] = {"failed_download_requests": FAILED_DOWNLOAD_REQUESTS}
    for name, extra in (
        ("product_parameters", {}),
        ("with_retries_10", {"retries": 10, "fragment_retries": 10}),
    ):
        with tempfile.TemporaryDirectory(prefix="qmd-retries-") as directory:
            results[name] = download_with(Path(directory), extra)
    return results


def sqlite_backup_experiment() -> dict[str, Any]:
    """UC-23: copia con la API de SQLite mientras otro hilo escribe en WAL."""
    with tempfile.TemporaryDirectory(prefix="qmd-backup-") as directory:
        source_path = Path(directory) / "queue.sqlite3"
        setup = sqlite3.connect(source_path)
        setup.execute("PRAGMA journal_mode=WAL")
        setup.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY, payload TEXT)")
        setup.execute("CREATE TABLE counter (total INTEGER)")
        setup.execute("INSERT INTO counter VALUES (0)")
        setup.commit()
        setup.close()
        stop = threading.Event()
        written = [0]

        def writer() -> None:
            connection = sqlite3.connect(source_path, timeout=30)
            while not stop.is_set():
                with connection:
                    connection.execute(
                        "INSERT INTO jobs (payload) VALUES (?)", ("x" * 512,)
                    )
                    connection.execute("UPDATE counter SET total = total + 1")
                written[0] += 1
            connection.close()

        thread = threading.Thread(target=writer)
        thread.start()
        while written[0] < 200:
            pass
        copies = []
        for attempt in range(5):
            source = sqlite3.connect(source_path, timeout=30)
            destination_path = Path(directory) / f"backup-{attempt}.sqlite3"
            destination = sqlite3.connect(destination_path)
            source.backup(destination, pages=8)
            source.close()
            integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
            rows = destination.execute("SELECT count(*) FROM jobs").fetchone()[0]
            total = destination.execute("SELECT total FROM counter").fetchone()[0]
            destination.close()
            copies.append({"integrity": integrity, "rows": rows, "counter": total})
        stop.set()
        thread.join()
    return {
        "copies": copies,
        "all_consistent": all(
            copy["integrity"] == "ok" and copy["rows"] == copy["counter"]
            for copy in copies
        ),
        "writes_during_experiment": written[0],
    }


def walk_cause_chain(error: BaseException) -> list[dict[str, Any]]:
    """Prototipo de BR-25: recorre exc_info, __cause__ y __context__ sin ciclos."""
    seen: set[int] = set()
    pending: list[BaseException] = [error]
    found: list[dict[str, Any]] = []
    while pending:
        current = pending.pop(0)
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, OSError):
            found.append(
                {
                    "type": type(current).__name__,
                    "errno": current.errno,
                    "winerror": getattr(current, "winerror", None),
                }
            )
        exc_info = getattr(current, "exc_info", None)
        if isinstance(exc_info, tuple) and isinstance(exc_info[1], BaseException):
            pending.append(exc_info[1])
        for linked in (current.__cause__, current.__context__):
            if linked is not None:
                pending.append(linked)
    return found


NO_SPACE = OSError(errno.ENOSPC, "No space left on device")


def _write_data(ydl: YoutubeDL) -> None:
    try:
        raise NO_SPACE
    except OSError as err:
        ydl.report_error(f"unable to write data: {err}")


def _create_directory(ydl: YoutubeDL) -> None:
    try:
        raise NO_SPACE
    except OSError as err:
        ydl.report_error(f"Unable to create directory: {err}")


def _file_access_exhausted(ydl: YoutubeDL) -> None:
    ydl.report_error(f"Unable to rename file: {NO_SPACE}")


def _process_info(ydl: YoutubeDL) -> None:
    try:
        try:
            raise NO_SPACE
        except OSError as err:
            raise UnavailableVideoError(err) from None
    except UnavailableVideoError as wrapped:
        wrapped.__context__ = NO_SPACE
        ydl.report_error(wrapped)


def _ffmpeg(ydl: YoutubeDL) -> None:
    try:
        raise FFmpegPostProcessorError("Error writing trailer: No space left on device")
    except FFmpegPostProcessorError as err:
        ydl.report_error(str(err))


STORAGE_ERROR_PATHS = {
    "write_data": _write_data,
    "create_directory": _create_directory,
    "file_access_exhausted": _file_access_exhausted,
    "process_info": _process_info,
    "ffmpeg": _ffmpeg,
}


def _captured(action: Any, ydl: YoutubeDL) -> DownloadError:
    try:
        action(ydl)
    except DownloadError as error:
        return error
    raise AssertionError("yt-dlp did not raise DownloadError")


def storage_error_paths() -> dict[str, DownloadError]:
    """Los cinco caminos, provocados en el mismo punto que en yt-dlp 2026.11.23."""
    ydl = YoutubeDL({"quiet": True, "logger": None})
    return {
        name: _captured(action, ydl) for name, action in STORAGE_ERROR_PATHS.items()
    }


def cause_chain_experiment() -> dict[str, Any]:
    """R-28: códigos recuperables por camino frente al clasificador actual."""
    results = {}
    for name, error in storage_error_paths().items():
        codes = walk_cause_chain(error)
        results[name] = {
            "current_reason": classify_failure(error).failure_reason.name,
            "codes_in_chain": codes,
            "needs_text": not codes,
            "text": str(error),
        }
    return results


def main() -> int:
    """Ejecuta los experimentos y escribe sus resultados."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()
    report = {
        "yt_dlp": yt_dlp.version.__version__,
        "python": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "retries": retries_experiment(),
        "sqlite_backup": sqlite_backup_experiment(),
        "cause_chain": cause_chain_experiment(),
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if arguments.output:
        arguments.output.write_text(text + os.linesep, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
