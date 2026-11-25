"""MediaSource implementada con la librería yt-dlp."""

import logging
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled

from queued_media_downloader.jobs import (
    FailureReason,
    Job,
    JobCompleted,
    JobEvent,
    JobFailed,
)
from queued_media_downloader.media_extraction.failure_classifier import (
    classify_failure,
    is_format_unavailable,
)
from queued_media_downloader.media_extraction.media_source import (
    JobCancelledError,
    Publish,
)
from queued_media_downloader.media_extraction.media_source_settings import (
    MediaSourceSettings,
)
from queued_media_downloader.media_extraction.partial_files import (
    remove_partial_directory,
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
                    _cancellable(publish),
                    self._media_source_settings.playlist_batch_size,
                )
        except YtDlpJobCancelled as cancellation:
            raise JobCancelledError from cancellation
        except Exception as extraction_error:
            publish(classify_failure(extraction_error))

    def download(self, job: Job, publish: Publish) -> None:
        """Descarga el contenido y publica el formato, el avance y el resultado.

        Los parciales van a la carpeta propia del job (T44). Al reanudar se pide
        el formato del primer intento, para que su .part siga siendo válido
        (ADR-0010); si el sitio ya no lo ofrece, se reintenta una sola vez con el
        format selector original (UC-06, A1). Solo se publica JobCompleted si la
        descarga y el postprocesado terminaron (_unfinished_download_failure);
        entonces se borra la carpeta de parciales, con lo que haya dejado
        cualquier intento anterior.
        """
        partial_directory = job.partial_directory()
        retry_with_format_selector = False
        publish = _cancellable(publish)
        try:
            final_path = self._download_with_format(
                job, job.selected_format_id, partial_directory, publish
            )
        except YtDlpJobCancelled as cancellation:
            raise JobCancelledError from cancellation
        except Exception as download_error:
            if job.selected_format_id is None or not is_format_unavailable(
                download_error
            ):
                publish(classify_failure(download_error))
                return
            retry_with_format_selector = True
        if retry_with_format_selector:
            # Fuera del except: yt-dlp tomaría el error del primer intento como
            # causa del segundo (sys.exc_info) y la clasificación sería otra.
            logger.info(
                "Format %s is no longer available; retrying with %s",
                job.selected_format_id,
                job.download_options.format_selector,
            )
            try:
                final_path = self._download_with_format(
                    job, None, partial_directory, publish
                )
            except YtDlpJobCancelled as cancellation:
                raise JobCancelledError from cancellation
            except Exception as retry_error:
                publish(classify_failure(retry_error))
                return
        unfinished_failure = _unfinished_download_failure(final_path, partial_directory)
        if unfinished_failure is not None:
            publish(unfinished_failure)
            return
        remove_partial_directory(partial_directory)
        publish(JobCompleted(output_path=final_path))

    def _download_with_format(
        self,
        job: Job,
        format_id: str | None,
        partial_directory: Path,
        publish: Publish,
    ) -> str | None:
        """Descarga con format_id o, sin él, con el format selector del job.

        Returns:
            La ruta final que yt-dlp registró tras mover el archivo.

        Raises:
            YtDlpReturnCodeError: Si yt-dlp terminó con un código distinto de 0.
        """
        parameters = build_yt_dlp_parameters(
            job.download_options,
            self._media_source_settings,
            job.playlist_context,
            partial_directory,
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
            return_code = youtube_dl.download([job.url])
        if return_code != 0:
            raise YtDlpReturnCodeError(return_code)
        return final_path_recorder.final_path

    def _download_progress(self, publish: Publish) -> DownloadProgressTranslator:
        """Traductor de progreso con el intervalo de la configuración."""
        return DownloadProgressTranslator(
            publish,
            interval_seconds=self._media_source_settings.progress_interval_seconds,
        )


class YtDlpJobCancelled(DownloadCancelled):  # type: ignore[misc]
    """JobCancelledError dentro de yt-dlp.

    yt-dlp deja salir DownloadCancelled de sus hooks y de download() sin
    convertirla en un error (YoutubeDL.download), así que la cancelación llega
    hasta esta MediaSource, que la devuelve como JobCancelledError.
    """


def _cancellable(publish: Publish) -> Publish:
    """Publish cuya JobCancelledError atraviesa yt-dlp como DownloadCancelled."""

    def publish_inside_yt_dlp(job_event: JobEvent) -> None:
        try:
            publish(job_event)
        except JobCancelledError as cancellation:
            raise YtDlpJobCancelled from cancellation

    return publish_inside_yt_dlp


class YtDlpReturnCodeError(Exception):
    """yt-dlp terminó con un código distinto de 0 sin lanzar una excepción."""

    def __init__(self, return_code: int) -> None:
        """Guarda el código que devolvió YoutubeDL.download."""
        self.return_code = return_code
        super().__init__(f"yt-dlp reported errors (return code {return_code})")


def _unfinished_download_failure(
    final_path: str | None, partial_directory: Path
) -> JobFailed | None:
    """JobFailed si la descarga no terminó con un archivo final utilizable.

    yt-dlp solo ejecuta los postprocessors after_move, donde se registra
    final_path, tras todos los de post_process y tras mover el archivo a su
    carpeta final (YoutubeDL.post_process). Una ruta registrada fuera de la
    carpeta de parciales y con contenido es, por tanto, un archivo terminado.
    """
    if final_path is None:
        return _filesystem_failure("The download finished without an output file")
    output_path = Path(final_path)
    if output_path.absolute().is_relative_to(partial_directory.absolute()):
        return _filesystem_failure(
            f"The output file was not moved out of its partial directory: {output_path}"
        )
    if not output_path.is_file() or output_path.stat().st_size == 0:
        return _filesystem_failure(
            f"The output file is missing or empty: {output_path}"
        )
    return None


def _filesystem_failure(failure_message: str) -> JobFailed:
    return JobFailed(
        failure_reason=FailureReason.FILESYSTEM, failure_message=failure_message
    )
