"""Parámetros de YoutubeDL que se fijan en cada job (diseño, Parte 2, §1.3)."""

import logging
from pathlib import Path
from typing import Any

from queued_media_downloader.jobs import DownloadOptions
from queued_media_downloader.media_extraction.media_source_settings import (
    MediaSourceSettings,
)

YT_DLP_LOGGER_NAME = "queued_media_downloader.yt_dlp"

# Extrae el audio sin recodificarlo cuando el formato lo permite.
EXTRACT_AUDIO_POSTPROCESSOR = {"key": "FFmpegExtractAudio", "preferredcodec": "best"}

# Los jobs de solo audio descargan en una subcarpeta propia. Con la misma
# carpeta y plantilla, su descarga intermedia (por ejemplo, Opus en .webm) puede
# llamarse igual que el video unido de otro job: yt-dlp la daría por descargada
# y FFmpegExtractAudio borraría ese video al terminar (hallado en T19).
AUDIO_ONLY_SUBDIRECTORY_NAME = "audio"

# Reintentos ante archivos bloqueados un instante, algo habitual en Windows
# cuando el antivirus o el indexador abren el archivo recién escrito.
FILE_ACCESS_RETRIES = 10


class YtDlpLogger:
    """Envía los mensajes de yt-dlp a logging en lugar de a la consola.

    yt-dlp llama a debug también para los mensajes de pantalla; la
    presentación del progreso es cosa de la línea de comandos.
    """

    def __init__(self) -> None:
        """Usa el logger de yt-dlp del proyecto."""
        self._logger = logging.getLogger(YT_DLP_LOGGER_NAME)

    def debug(self, message: str) -> None:
        """Registra un mensaje de pantalla o de depuración."""
        self._logger.debug(message)

    def info(self, message: str) -> None:
        """Registra un mensaje informativo."""
        self._logger.info(message)

    def warning(self, message: str) -> None:
        """Registra una advertencia."""
        self._logger.warning(message)

    def error(self, message: str) -> None:
        """Registra un error."""
        self._logger.error(message)


def build_yt_dlp_parameters(
    download_options: DownloadOptions, media_source_settings: MediaSourceSettings
) -> dict[str, Any]:
    """Construye los parámetros de un YoutubeDL nuevo para un job.

    Cada job usa su propio YoutubeDL, así que nada se arrastra de un job a otro.
    """
    parameters: dict[str, Any] = {
        "format": download_options.format_selector,
        "paths": {"home": str(_download_directory_of(download_options))},
        "outtmpl": {"default": download_options.output_template},
        "cachedir": str(media_source_settings.cache_directory),
        "trim_file_name": media_source_settings.max_filename_length,
        "js_runtimes": {"deno": {}},
        "continuedl": True,
        # Un enlace a un video dentro de una lista (watch?v=…&list=…) descarga
        # solo el video; la lista se encola con su propia URL (ADR-0027).
        "noplaylist": True,
        "noprogress": True,
        # Sin secuencias de terminal: los mensajes de yt-dlp van al log y a los
        # job events, nunca a una consola. Con color, "ERROR:" llegaba envuelto
        # en códigos ANSI y el prefijo no se podía quitar (T19, en Windows).
        "color": "never",
        "file_access_retries": FILE_ACCESS_RETRIES,
        "logger": YtDlpLogger(),
    }
    if download_options.audio_only:
        # También cubre un formato con video: de él se extrae solo el audio.
        parameters["postprocessors"] = [dict(EXTRACT_AUDIO_POSTPROCESSOR)]
    if media_source_settings.ffmpeg_location is not None:
        parameters["ffmpeg_location"] = str(media_source_settings.ffmpeg_location)
    return parameters


def _download_directory_of(download_options: DownloadOptions) -> Path:
    """Carpeta de destino; la de solo audio nunca coincide con la de los videos."""
    if download_options.audio_only:
        return download_options.download_directory / AUDIO_ONLY_SUBDIRECTORY_NAME
    return download_options.download_directory
