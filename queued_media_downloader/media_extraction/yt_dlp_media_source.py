"""MediaSource implementada con la librería yt-dlp."""

from yt_dlp import YoutubeDL

from queued_media_downloader.jobs import (
    Job,
    JobCompleted,
)
from queued_media_downloader.media_extraction.failure_classifier import (
    classify_failure,
)
from queued_media_downloader.media_extraction.media_source import Publish
from queued_media_downloader.media_extraction.media_source_settings import (
    MediaSourceSettings,
)
from queued_media_downloader.media_extraction.progress_event_translator import (
    DownloadProgressTranslator,
    PostprocessingProgressTranslator,
)
from queued_media_downloader.media_extraction.recording_postprocessors import (
    RECORDING_POSTPROCESSOR_NAMES,
    FinalPathRecorder,
    SelectedFormatRecorder,
)
from queued_media_downloader.media_extraction.yt_dlp_expansion import expand_url
from queued_media_downloader.media_extraction.yt_dlp_parameters import (
    build_yt_dlp_parameters,
)


class YtDlpMediaSource:
    """Expande y descarga jobs con yt-dlp; un YoutubeDL nuevo por job.

    Los fallos no se propagan: se publican como JobFailed, para que el worker
    siga con el siguiente job.
    """

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
        try:
            # Las entradas de una playlist se recorren dentro del bloque: yt-dlp
            # puede pedir más páginas mientras se iteran.
            with YoutubeDL(parameters) as youtube_dl:
                expand_url(
                    youtube_dl,
                    job.url,
                    publish,
                    self._media_source_settings.playlist_batch_size,
                )
        except Exception as extraction_error:
            publish(classify_failure(extraction_error))

    def download(self, job: Job, publish: Publish) -> None:
        """Descarga el contenido y publica el formato, el avance y el resultado."""
        parameters = build_yt_dlp_parameters(
            job.download_options, self._media_source_settings
        )
        if job.selected_format_id is not None:
            # Al reanudar se pide el mismo formato que en el primer intento,
            # para que el .part siga siendo válido (ADR-0010).
            parameters["format"] = job.selected_format_id
        parameters["progress_hooks"] = [self._download_progress(publish).translate]
        parameters["postprocessor_hooks"] = [
            PostprocessingProgressTranslator(
                publish, ignored_postprocessor_names=RECORDING_POSTPROCESSOR_NAMES
            ).translate
        ]
        final_path_recorder = FinalPathRecorder()
        try:
            with YoutubeDL(parameters) as youtube_dl:
                youtube_dl.add_post_processor(
                    SelectedFormatRecorder(publish), when="before_dl"
                )
                youtube_dl.add_post_processor(final_path_recorder, when="after_move")
                youtube_dl.download([job.url])
        except Exception as download_error:
            publish(classify_failure(download_error))
            return
        publish(JobCompleted(output_path=final_path_recorder.final_path))

    def _download_progress(self, publish: Publish) -> DownloadProgressTranslator:
        """Traductor de progreso con el intervalo de la configuración."""
        return DownloadProgressTranslator(
            publish,
            interval_seconds=self._media_source_settings.progress_interval_seconds,
        )
