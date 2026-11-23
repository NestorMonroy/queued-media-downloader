"""Traduce los hooks de progreso de yt-dlp a job events.

yt-dlp llama al hook de descarga en cada bloque recibido; publicar cada llamada
saturaría la cola hacia el proceso principal, así que se limita a una por
intervalo (diseño, Parte 2, §1.3).
"""

import time
from collections.abc import Callable, Mapping
from typing import Any

from queued_media_downloader.jobs import (
    DownloadProgressed,
    PostprocessingProgressed,
    PostprocessingStage,
)
from queued_media_downloader.media_extraction.media_source import Publish


class DownloadProgressTranslator:
    """Convierte los progress_hooks de yt-dlp en DownloadProgressed."""

    def __init__(
        self,
        publish: Publish,
        *,
        interval_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Publica como máximo un evento cada interval_seconds según clock."""
        self._publish = publish
        self._interval_seconds = interval_seconds
        self._clock = clock
        self._last_published_at: float | None = None

    def translate(self, hook: Mapping[str, Any]) -> None:
        """Publica el avance si toca; el final de un archivo siempre se publica."""
        status = hook.get("status")
        if status == "finished" or (
            status == "downloading" and self._interval_elapsed()
        ):
            self._last_published_at = self._clock()
            self._publish(_download_progressed_from(hook))

    def _interval_elapsed(self) -> bool:
        """Indica si pasó el intervalo desde la última publicación."""
        if self._last_published_at is None:
            return True
        return self._clock() - self._last_published_at >= self._interval_seconds


def _download_progressed_from(hook: Mapping[str, Any]) -> DownloadProgressed:
    """Toma del hook solo los valores numéricos; los textos con formato no viajan."""
    total_bytes = hook.get("total_bytes") or hook.get("total_bytes_estimate")
    downloaded_bytes = hook.get("downloaded_bytes")
    eta = hook.get("eta")
    if hook.get("status") == "finished":
        eta = 0
        # Un archivo que ya estaba en disco llega terminado y sin
        # downloaded_bytes: está completo.
        downloaded_bytes = downloaded_bytes or total_bytes
    return DownloadProgressed(
        downloaded_bytes=int(downloaded_bytes or 0),
        total_bytes=None if total_bytes is None else int(total_bytes),
        bytes_per_second=hook.get("speed"),
        eta_seconds=None if eta is None else int(eta),
    )


class PostprocessingProgressTranslator:
    """Convierte los postprocessor_hooks de yt-dlp en PostprocessingProgressed."""

    def __init__(
        self, publish: Publish, *, ignored_postprocessor_names: frozenset[str]
    ) -> None:
        """No publica nada de los postprocessors de ignored_postprocessor_names.

        Los postprocessors de registro del proyecto también disparan el hook,
        pero no son un avance que interese al usuario.
        """
        self._publish = publish
        self._ignored_postprocessor_names = ignored_postprocessor_names

    def translate(self, hook: Mapping[str, Any]) -> None:
        """Publica la etapa del postprocessor, salvo que esté ignorado."""
        postprocessor_name = str(hook.get("postprocessor", ""))
        if postprocessor_name in self._ignored_postprocessor_names:
            return
        self._publish(
            PostprocessingProgressed(
                postprocessor_name=postprocessor_name,
                postprocessing_stage=PostprocessingStage(str(hook["status"]).upper()),
            )
        )
