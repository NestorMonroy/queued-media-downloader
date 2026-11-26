"""Regresión de T42-D3: los retos de JavaScript de YouTube se resuelven.

En la campaña de Windows (yt-dlp 2026.10.26), el solucionador de yt-dlp-ejs
fallaba con el reproductor por defecto (variante main) y yt-dlp avisaba de que
podían faltar formatos. yt-dlp 2026.11.23 usa la variante tv por defecto. Esta
prueba descarga el video que usa yt-dlp en sus pruebas y exige que el log de
la cola no tenga ese aviso. Necesita red (marcador network): en el entorno de
desarrollo el proxy bloquea YouTube; se ejecuta en la campaña de Windows.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from queued_media_downloader.command_line import main
from queued_media_downloader.jobs import Job, JobStatus

VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
# Avisos de yt-dlp cuando un reto no se resuelve (yt_dlp/extractor/youtube).
CHALLENGE_FAILURE_TEXTS = ("challenge solving failed", "Error solving")


@pytest.mark.network
def test_a_youtube_download_solves_its_javascript_challenges(
    state_directory: Path,
    read_stored_job: Callable[[int], Job],
) -> None:
    main(["enqueue", VIDEO_URL])

    exit_code = main(["run"])

    log_text = (state_directory / "logs" / "queued-media-downloader.log").read_text(
        encoding="utf-8"
    )
    job = read_stored_job(1)
    assert exit_code == 0
    assert job.status is JobStatus.COMPLETED
    assert "[jsc:deno] Solving JS challenges using deno" in log_text
    assert not [text for text in CHALLENGE_FAILURE_TEXTS if text in log_text]
