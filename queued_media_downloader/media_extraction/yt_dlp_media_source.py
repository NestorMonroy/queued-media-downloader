"""MediaSource implementada con la librería yt-dlp."""

from typing import Any

from yt_dlp import YoutubeDL

from queued_media_downloader.jobs import (
    FailureReason,
    Job,
    JobFailed,
    MediaKey,
    SingleMediaFound,
)
from queued_media_downloader.media_extraction.media_source import Publish
from queued_media_downloader.media_extraction.media_source_settings import (
    MediaSourceSettings,
)
from queued_media_downloader.media_extraction.yt_dlp_parameters import (
    build_yt_dlp_parameters,
)

# Tipos de resultado de yt-dlp que son un solo contenido. Un multi_video (un
# contenido partido en varios videos) también lo es (diseño, Parte 2, §1.2).
SINGLE_MEDIA_RESULT_TYPES = frozenset({"video", "multi_video"})


class YtDlpMediaSource:
    """Expande y descarga jobs con yt-dlp; un YoutubeDL nuevo por job."""

    def __init__(self, media_source_settings: MediaSourceSettings) -> None:
        """Guarda la configuración común a todos los jobs."""
        self._media_source_settings = media_source_settings

    def expand(self, job: Job, publish: Publish) -> None:
        """Extrae la URL sin procesarla ni descargarla y publica qué encontró.

        En E1 solo se admite un contenido único; las playlists llegan con UC-04.
        """
        parameters = build_yt_dlp_parameters(
            job.download_options, self._media_source_settings
        )
        with YoutubeDL(parameters) as youtube_dl:
            # process=False no resuelve formatos ni recorre playlists: solo
            # identifica qué hay detrás de la URL.
            result = youtube_dl.extract_info(job.url, download=False, process=False)
        result_type = result.get("_type", "video")
        if result_type in SINGLE_MEDIA_RESULT_TYPES:
            publish(_single_media_found_from(result))
        else:
            publish(
                JobFailed(
                    failure_reason=FailureReason.UNSUPPORTED_URL,
                    failure_message=f"Results of type {result_type} are not supported",
                )
            )


def _single_media_found_from(result: dict[str, Any]) -> SingleMediaFound:
    """Toma del resultado de yt-dlp solo la identidad y el título del contenido."""
    media_id = str(result["id"])
    return SingleMediaFound(
        media_key=MediaKey(extractor_key=result["extractor_key"], media_id=media_id),
        title=result.get("title") or media_id,
    )
