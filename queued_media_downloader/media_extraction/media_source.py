"""Contrato de extracción y descarga de contenidos.

No importa yt_dlp: workers/ depende de este contrato y no de la librería.
"""

from collections.abc import Callable
from typing import Protocol

from queued_media_downloader.jobs import Job, JobEvent

Publish = Callable[[JobEvent], None]


class JobCancelledError(Exception):
    """El User canceló el job en curso (UC-05, paso 5).

    La lanza publish, en el worker, al publicar un job event que no es final
    cuando el job tiene pedida su cancelación. Una MediaSource debe dejarla
    salir sin convertirla en un fallo.
    """


class MediaSource(Protocol):
    """Expande y descarga jobs; informa de lo que ocurre publicando job events.

    publish puede lanzar JobCancelledError: la MediaSource debe dejarla salir,
    sin publicar nada más.
    """

    def expand(self, job: Job, publish: Publish) -> None:
        """Averigua si la URL del job es un contenido o una playlist.

        Publica SingleMediaFound si es un solo contenido. No descarga nada.
        """
        ...

    def download(self, job: Job, publish: Publish) -> None:
        """Descarga el contenido del job y publica su avance y su resultado."""
        ...
