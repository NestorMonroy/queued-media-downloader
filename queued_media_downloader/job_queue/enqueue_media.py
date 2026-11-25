"""Caso de uso UC-02: encolar contenido."""

from collections.abc import Sequence
from urllib.parse import urlsplit

from queued_media_downloader.job_storage import JobStore
from queued_media_downloader.jobs import DownloadOptions, Job, JobId

SUPPORTED_URL_SCHEMES = frozenset({"http", "https"})


class InvalidUrlError(Exception):
    """La URL no tiene la forma de una dirección http o https."""

    def __init__(self, url: str) -> None:
        """Guarda la URL y compone el mensaje que verá el usuario."""
        self.url = url
        super().__init__(f"Invalid URL {url!r}: expected an http or https address")


class EnqueueMedia:
    """Crea un job de expansión por URL, sin extraer ni descargar nada."""

    def __init__(self, job_store: JobStore) -> None:
        """Usa job_store para guardar los jobs creados."""
        self._job_store = job_store

    def execute(
        self, urls: Sequence[str], download_options: DownloadOptions
    ) -> list[JobId]:
        """Encola las URLs con las download options fijadas en este momento.

        Todas las URLs se validan antes de crear el primer job, para que una
        URL no válida no deje la invocación a medias (UC-02 A1).

        Returns:
            Los identificadores de los jobs creados, en el orden de las URLs.

        Raises:
            InvalidUrlError: Si alguna URL no es válida; no se crea ningún job.
            JobStoreLockedError: Si la base de datos sigue bloqueada tras su
                espera (UC-02 A3); no se crea ningún job.
        """
        for url in urls:
            _ensure_valid_url(url)
        # Una sola transacción: o se encolan todas o ninguna.
        return self._job_store.create_many(
            [Job.new_expansion(url, download_options) for url in urls]
        )


def _ensure_valid_url(url: str) -> None:
    """Comprueba solo la forma de la URL: enqueue no accede a la red."""
    parts = urlsplit(url)
    if parts.scheme not in SUPPORTED_URL_SCHEMES or not parts.netloc:
        raise InvalidUrlError(url)
