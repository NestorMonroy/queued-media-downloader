"""Protección de los datos reales del usuario durante las pruebas (auditoría §5).

Ninguna prueba puede leer ni escribir el estado real (base de datos, registro,
caché de yt-dlp, carpetas de parciales), las descargas reales ni config.toml.
Dos defensas:

1. isolate_environment: cada prueba recibe carpetas de estado y descargas
   propias (variables QUEUED_MEDIA_DOWNLOADER_*) y un config.toml propio.
2. RealDataSnapshot: antes y después de la sesión se toma una huella de cada
   archivo de las ubicaciones reales (ruta relativa, tamaño, fecha de
   modificación en ns y SHA-256). Cualquier archivo creado, borrado o
   cambiado hace fallar la sesión, aunque el número de archivos o de filas
   no cambie.
"""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from queued_media_downloader.command_line import command_settings
from queued_media_downloader.configuration import project_root

ENVIRONMENT_PREFIX = "QUEUED_MEDIA_DOWNLOADER_"
# Se copia al importar, antes de que isolate_environment lo reemplace.
REAL_CONFIG_FILE_NAME = command_settings.CONFIG_FILE_NAME


def real_locations() -> dict[str, Path]:
    """Ubicaciones por defecto del programa, las que usa el Responsable."""
    return {
        "state": project_root() / "state",
        "downloads": Path.home() / "Downloads" / "queued-media-downloader",
        "config": project_root() / REAL_CONFIG_FILE_NAME,
    }


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    """Huella de un archivo: basta un byte o una fecha distinta para notarlo."""

    size: int
    modified_ns: int
    sha256: str


def _fingerprint(path: Path) -> FileFingerprint:
    status = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return FileFingerprint(status.st_size, status.st_mtime_ns, digest)


@dataclass(frozen=True, slots=True)
class RealDataSnapshot:
    """Huellas de todos los archivos bajo unas ubicaciones, por ruta."""

    files: dict[str, FileFingerprint]

    @classmethod
    def take(cls, locations: dict[str, Path]) -> "RealDataSnapshot":
        """Recorre las ubicaciones sin modificarlas (solo stat y lectura)."""
        files: dict[str, FileFingerprint] = {}
        for name, location in locations.items():
            if location.is_file():
                files[name] = _fingerprint(location)
            elif location.is_dir():
                for directory, _, file_names in os.walk(location):
                    for file_name in file_names:
                        path = Path(directory) / file_name
                        relative = path.relative_to(location).as_posix()
                        files[f"{name}/{relative}"] = _fingerprint(path)
        return cls(files)

    def differences(self, later: "RealDataSnapshot") -> list[str]:
        """Archivos creados, borrados o cambiados entre las dos huellas."""
        created = sorted(later.files.keys() - self.files.keys())
        deleted = sorted(self.files.keys() - later.files.keys())
        changed = sorted(
            path
            for path in self.files.keys() & later.files.keys()
            if self.files[path] != later.files[path]
        )
        return (
            [f"created: {path}" for path in created]
            + [f"deleted: {path}" for path in deleted]
            + [f"changed: {path}" for path in changed]
        )


def isolate_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Da a la prueba estado, descargas y config.toml propios en tmp_path."""
    for variable in list(os.environ):
        if variable.startswith(ENVIRONMENT_PREFIX):
            monkeypatch.delenv(variable)
    state_directory = tmp_path / "state"
    monkeypatch.setenv(f"{ENVIRONMENT_PREFIX}STATE_DIRECTORY", str(state_directory))
    monkeypatch.setenv(
        f"{ENVIRONMENT_PREFIX}DOWNLOAD_DIRECTORY", str(tmp_path / "downloads")
    )
    # project_root() / ruta absoluta da la ruta absoluta: config.toml propio.
    monkeypatch.setattr(
        command_settings, "CONFIG_FILE_NAME", str(tmp_path / "config.toml")
    )
    return state_directory
