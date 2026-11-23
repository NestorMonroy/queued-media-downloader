"""Pregunta a yt-dlp qué deno usará, para informar del mismo que usa al descargar.

yt-dlp busca deno primero junto al Python del entorno virtual, donde lo instala
el extra deno de pyproject.toml (ADR-0003), y después en el PATH.
"""

from pathlib import Path

from yt_dlp.utils._jsruntime import DenoJsRuntime

from queued_media_downloader.media_extraction.javascript_runtime import (
    JavaScriptRuntime,
)


def find_deno() -> JavaScriptRuntime | None:
    """Deno que yt-dlp encontraría; None si no hay ninguno que responda.

    Usa un módulo interno de yt-dlp: la versión está fijada y esta función
    tiene una prueba de contrato.
    """
    deno_info = DenoJsRuntime().info
    if deno_info is None:
        return None
    return JavaScriptRuntime(
        name=deno_info.name,
        path=Path(deno_info.path),
        version=deno_info.version,
        minimum_version=".".join(map(str, DenoJsRuntime.MIN_SUPPORTED_VERSION)),
        is_supported=deno_info.supported,
    )
