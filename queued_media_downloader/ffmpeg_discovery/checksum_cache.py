"""SHA-256 de archivos, recalculado solo si cambian su tamaño o su fecha.

Calcular el SHA-256 de los ~150 MiB de la build en cada arranque sería lento en
un equipo modesto (ADR-0006).
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

READ_CHUNK_BYTES = 1024 * 1024


class ChecksumCache:
    """Guarda en un archivo JSON el SHA-256, el tamaño y la fecha de cada archivo."""

    def __init__(self, cache_file: Path) -> None:
        """Carga la caché de cache_file; si falta o no se puede leer, empieza vacía."""
        self._cache_file = cache_file
        self._entries = _load_entries(cache_file)
        self._changed = False

    def sha256_of(self, path: Path) -> str:
        """SHA-256 de path, de la caché si el archivo no cambió."""
        status = path.stat()
        key = str(path.resolve())
        entry = self._entries.get(key)
        if (
            isinstance(entry, dict)
            and entry.get("size") == status.st_size
            and entry.get("mtime_ns") == status.st_mtime_ns
            and isinstance(entry.get("sha256"), str)
        ):
            return str(entry["sha256"])
        sha256 = _compute_sha256(path)
        self._entries[key] = {
            "size": status.st_size,
            "mtime_ns": status.st_mtime_ns,
            "sha256": sha256,
        }
        self._changed = True
        return sha256

    def save(self) -> None:
        """Escribe la caché si cambió, de una vez para no dejarla a medias."""
        if not self._changed:
            return
        self._cache_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = self._cache_file.with_suffix(".tmp")
        temporary_file.write_text(
            json.dumps(self._entries, indent=2, sort_keys=True), encoding="utf-8"
        )
        temporary_file.replace(self._cache_file)
        self._changed = False


def _load_entries(cache_file: Path) -> dict[str, Any]:
    """Entradas guardadas; una caché ilegible se descarta y se reconstruye."""
    try:
        entries = json.loads(cache_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        logger.warning("Ignoring unreadable checksum cache %s", cache_file)
        return {}
    return entries if isinstance(entries, dict) else {}


def _compute_sha256(path: Path) -> str:
    """SHA-256 leyendo el archivo por bloques, sin cargarlo entero en memoria."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(READ_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()
