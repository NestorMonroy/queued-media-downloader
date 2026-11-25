"""Configuración del programa, ya validada."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class Settings:
    """Valores de configuración de una ejecución (diseño, Parte 2, §4.2).

    Solo se crean con load_settings, que aplica el orden de prioridad y la
    validación de cada valor.
    """

    download_directory: Path
    state_directory: Path
    worker_count: int
    progress_interval_seconds: float
    cancellation_grace_seconds: float
    default_format_selector: str
    single_media_output_template: str
    max_filename_length: int
    ffmpeg_path: Path | None
