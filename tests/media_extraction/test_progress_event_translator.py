from typing import Any

from queued_media_downloader.jobs import (
    DownloadProgressed,
    JobEvent,
    PostprocessingProgressed,
    PostprocessingStage,
)
from queued_media_downloader.media_extraction.progress_event_translator import (
    DownloadProgressTranslator,
    PostprocessingProgressTranslator,
)

# Diccionarios grabados de una descarga real de yt-dlp 2026.10.26 contra el
# servidor local (sin info_dict ni los campos de texto con formato).
RECORDED_FIRST_DOWNLOADING_HOOK: dict[str, Any] = {
    "status": "downloading",
    "downloaded_bytes": 1024,
    "total_bytes": 300000,
    "tmpfilename": "/tmp/out/sample [sample].mp4.part",
    "filename": "/tmp/out/sample [sample].mp4",
    "eta": None,
    "speed": None,
    "elapsed": 0.0031769275665283203,
    "ctx_id": None,
}
RECORDED_LAST_DOWNLOADING_HOOK: dict[str, Any] = {
    "status": "downloading",
    "downloaded_bytes": 300000,
    "total_bytes": 300000,
    "tmpfilename": "/tmp/out/sample [sample].mp4.part",
    "filename": "/tmp/out/sample [sample].mp4",
    "eta": 0,
    "speed": 82155340.82005745,
    "elapsed": 0.006601572036743164,
    "ctx_id": None,
}
RECORDED_FINISHED_HOOK: dict[str, Any] = {
    "downloaded_bytes": 300000,
    "total_bytes": 300000,
    "filename": "/tmp/out/sample [sample].mp4",
    "status": "finished",
    "elapsed": 0.0071980953216552734,
    "ctx_id": None,
    "speed": 41677692.02742539,
}


class FakeClock:
    """Reloj que solo avanza cuando la prueba lo indica."""

    def __init__(self) -> None:
        """Empieza en cero."""
        self.seconds = 0.0

    def __call__(self) -> float:
        """Devuelve la hora actual del reloj."""
        return self.seconds


def download_translator(
    published_events: list[JobEvent], clock: FakeClock
) -> DownloadProgressTranslator:
    """Traductor con un intervalo de medio segundo y el reloj de la prueba."""
    return DownloadProgressTranslator(
        published_events.append, interval_seconds=0.5, clock=clock
    )


def test_downloading_hook_becomes_download_progressed() -> None:
    published_events: list[JobEvent] = []
    translator = download_translator(published_events, FakeClock())

    translator.translate(RECORDED_LAST_DOWNLOADING_HOOK)

    assert published_events == [
        DownloadProgressed(
            downloaded_bytes=300000,
            total_bytes=300000,
            bytes_per_second=82155340.82005745,
            eta_seconds=0,
        )
    ]


def test_unknown_speed_and_eta_stay_unknown() -> None:
    published_events: list[JobEvent] = []
    translator = download_translator(published_events, FakeClock())

    translator.translate(RECORDED_FIRST_DOWNLOADING_HOOK)

    [job_event] = published_events
    assert isinstance(job_event, DownloadProgressed)
    assert job_event.bytes_per_second is None
    assert job_event.eta_seconds is None


def test_estimated_total_is_used_when_the_exact_total_is_unknown() -> None:
    published_events: list[JobEvent] = []
    translator = download_translator(published_events, FakeClock())
    hook = {
        **RECORDED_FIRST_DOWNLOADING_HOOK,
        "total_bytes": None,
        "total_bytes_estimate": 299000.5,
    }

    translator.translate(hook)

    [job_event] = published_events
    assert isinstance(job_event, DownloadProgressed)
    assert job_event.total_bytes == 299000


def test_downloading_hooks_are_published_at_most_once_per_interval() -> None:
    published_events: list[JobEvent] = []
    clock = FakeClock()
    translator = download_translator(published_events, clock)

    translator.translate(RECORDED_FIRST_DOWNLOADING_HOOK)
    clock.seconds = 0.4
    translator.translate(RECORDED_FIRST_DOWNLOADING_HOOK)
    clock.seconds = 0.5
    translator.translate(RECORDED_LAST_DOWNLOADING_HOOK)

    assert len(published_events) == 2


def test_finished_hook_is_always_published() -> None:
    published_events: list[JobEvent] = []
    translator = download_translator(published_events, FakeClock())

    translator.translate(RECORDED_LAST_DOWNLOADING_HOOK)
    translator.translate(RECORDED_FINISHED_HOOK)

    assert published_events[-1] == DownloadProgressed(
        downloaded_bytes=300000,
        total_bytes=300000,
        bytes_per_second=41677692.02742539,
        eta_seconds=0,
    )


def test_error_hook_is_not_published() -> None:
    published_events: list[JobEvent] = []
    translator = download_translator(published_events, FakeClock())

    translator.translate({**RECORDED_FIRST_DOWNLOADING_HOOK, "status": "error"})

    assert published_events == []


def test_postprocessor_hook_becomes_postprocessing_progressed() -> None:
    published_events: list[JobEvent] = []
    translator = PostprocessingProgressTranslator(
        published_events.append, ignored_postprocessor_names=frozenset()
    )

    translator.translate({"status": "started", "postprocessor": "Merger"})
    translator.translate({"status": "finished", "postprocessor": "Merger"})

    assert published_events == [
        PostprocessingProgressed(
            postprocessor_name="Merger",
            postprocessing_stage=PostprocessingStage.STARTED,
        ),
        PostprocessingProgressed(
            postprocessor_name="Merger",
            postprocessing_stage=PostprocessingStage.FINISHED,
        ),
    ]


def test_ignored_postprocessors_are_not_published() -> None:
    published_events: list[JobEvent] = []
    translator = PostprocessingProgressTranslator(
        published_events.append,
        ignored_postprocessor_names=frozenset({"SelectedFormatRecorder"}),
    )

    translator.translate(
        {"status": "started", "postprocessor": "SelectedFormatRecorder"}
    )

    assert published_events == []


def test_already_downloaded_file_is_presented_as_complete() -> None:
    # yt-dlp informa así de un archivo que ya estaba en disco: sin
    # downloaded_bytes (visto en la evaluación en Windows, T19).
    published_events: list[JobEvent] = []
    translator = download_translator(published_events, FakeClock())

    translator.translate(
        {"status": "finished", "filename": "video.webm", "total_bytes": 474521}
    )

    assert published_events == [
        DownloadProgressed(
            downloaded_bytes=474521,
            total_bytes=474521,
            bytes_per_second=None,
            eta_seconds=0,
        )
    ]
