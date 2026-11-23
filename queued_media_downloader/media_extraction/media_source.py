"""Contrato de extracción y descarga de contenidos.

No importa yt_dlp: workers/ depende de este contrato y no de la librería.
"""

from collections.abc import Callable
from typing import Protocol

from queued_media_downloader.jobs import Job, JobEvent

Publish = Callable[[JobEvent], None]


class MediaSource(Protocol):
    """Expande y descarga jobs; informa de lo que ocurre publicando job events."""

    def expand(self, job: Job, publish: Publish) -> None:
        """Averigua si la URL del job es un contenido o una playlist.

        Publica SingleMediaFound si es un solo contenido. No descarga nada.
        """
        ...

    def download(self, job: Job, publish: Publish) -> None:
        """Descarga el contenido del job y publica su avance y su resultado."""
        ...
