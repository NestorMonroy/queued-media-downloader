"""Opciones con las que se descarga un contenido."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DownloadOptions:
    """Opciones fijadas al encolar; viajan con el job aunque cambie la configuración."""

    format_selector: str
    download_directory: Path
    output_template: str
    audio_only: bool
    # Con un enlace a un video dentro de una lista, descargar la lista entera
    # en lugar de solo el video (ADR-0027).
    whole_playlist: bool = False
