"""Postprocessors de yt-dlp que solo registran datos de la descarga.

No modifican nada: yt-dlp los ejecuta en el momento justo en que el dato existe
(diseño, Parte 2, §1.3).
"""

from typing import Any

from yt_dlp.postprocessor import PostProcessor

from queued_media_downloader.jobs import FormatSelected
from queued_media_downloader.media_extraction.media_source import Publish


class RecordingPostProcessor(PostProcessor):  # type: ignore[misc]
    """Base de los postprocessors de registro."""

    @classmethod
    def pp_key(cls) -> str:
        """Usa el nombre completo de la clase en los hooks y los logs.

        yt-dlp quita los dos últimos caracteres porque espera el sufijo PP.
        """
        return cls.__name__


class SelectedFormatRecorder(RecordingPostProcessor):
    """Publica FormatSelected; se registra con when='before_dl'."""

    def __init__(self, publish: Publish) -> None:
        """Publica con publish el formato elegido."""
        super().__init__()
        self._publish = publish

    def run(self, info: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        """Publica el formato antes de descargar, para reutilizarlo al reanudar."""
        self._publish(FormatSelected(selected_format_id=str(info["format_id"])))
        return [], info


class FinalPathRecorder(RecordingPostProcessor):
    """Guarda la ruta final del archivo; se registra con when='after_move'.

    La ruta final puede diferir de la plantilla tras unir o convertir.
    """

    def __init__(self) -> None:
        """Empieza sin ruta: solo se conoce al terminar la descarga."""
        super().__init__()
        self.final_path: str | None = None

    def run(self, info: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        """Toma la ruta del archivo ya movido a su carpeta de destino."""
        self.final_path = info.get("filepath")
        return [], info


RECORDING_POSTPROCESSOR_NAMES = frozenset(
    {SelectedFormatRecorder.pp_key(), FinalPathRecorder.pp_key()}
)
