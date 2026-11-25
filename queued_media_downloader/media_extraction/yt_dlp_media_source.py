"""MediaSource implementada con la librería yt-dlp."""

import logging
from pathlib import Path

from yt_dlp import YoutubeDL

from queued_media_downloader.jobs import (
    Job,
    JobCompleted,
)
from queued_media_downloader.media_extraction.failure_classifier import (
    classify_failure,
    is_format_unavailable,
)
from queued_media_downloader.media_extraction.media_source import Publish
from queued_media_downloader.media_extraction.media_source_settings import (
    MediaSourceSettings,
)
from queued_media_downloader.media_extraction.partial_files import (
    remove_partial_files_of,
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

logger = logging.getLogger(__name__)


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

        Publica un contenido único o las entradas de la playlist por lotes.
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
        """Descarga el contenido y publica el formato, el avance y el resultado.

        Al reanudar se pide el formato del primer intento, para que su .part
        siga siendo válido (ADR-0010). Si el sitio ya no lo ofrece, se reintenta
        una vez con el format selector original y se borran los parciales del
        formato anterior (UC-06, A1).
        """
        try:
            final_path = self._download_with_format(
                job, job.selected_format_id, publish
            )
        except Exception as download_error:
            if job.selected_format_id is None or not is_format_unavailable(
                download_error
            ):
                publish(classify_failure(download_error))
                return
            logger.info(
                "Format %s is no longer available; retrying with %s",
                job.selected_format_id,
                job.download_options.format_selector,
            )
            try:
                final_path = self._download_with_format(job, None, publish)
            except Exception as retry_error:
                publish(classify_failure(retry_error))
                return
            if final_path is not None:
                remove_partial_files_of(Path(final_path))
        publish(JobCompleted(output_path=final_path))

    def _download_with_format(
        self, job: Job, format_id: str | None, publish: Publish
    ) -> str | None:
        """Descarga con format_id o, sin él, con el format selector del job.

        Returns:
            La ruta final del archivo.
        """
        parameters = build_yt_dlp_parameters(
            job.download_options, self._media_source_settings, job.playlist_context
        )
        if format_id is not None:
            parameters["format"] = format_id
        parameters["progress_hooks"] = [self._download_progress(publish).translate]
        parameters["postprocessor_hooks"] = [
            PostprocessingProgressTranslator(
                publish, ignored_postprocessor_names=RECORDING_POSTPROCESSOR_NAMES
            ).translate
        ]
        final_path_recorder = FinalPathRecorder()
        with YoutubeDL(parameters) as youtube_dl:
            youtube_dl.add_post_processor(
                SelectedFormatRecorder(publish), when="before_dl"
            )
            youtube_dl.add_post_processor(final_path_recorder, when="after_move")
            youtube_dl.download([job.url])
        return final_path_recorder.final_path

    def _download_progress(self, publish: Publish) -> DownloadProgressTranslator:
        """Traductor de progreso con el intervalo de la configuración."""
        return DownloadProgressTranslator(
            publish,
            interval_seconds=self._media_source_settings.progress_interval_seconds,
        )
