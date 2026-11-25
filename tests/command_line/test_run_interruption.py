"""Ctrl+C durante run (UC-05 A6), con señales reales a un proceso de run."""

import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from queued_media_downloader.command_line.command_parser import main
from queued_media_downloader.jobs import Job, JobStatus
from tests.conftest import SLOW_MEDIA_CONTENT, SLOW_MEDIA_NAME

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows: Ctrl+C is a console event; checked in the final campaign",
)
INTERRUPTION_EXIT_CODE = 130
WAIT_TIMEOUT_SECONDS = 60.0


def start_run(state_directory: Path, *options: str) -> subprocess.Popen[str]:
    """Arranca run como lo haría el User, con el mismo entorno de la prueba."""
    del state_directory
    return subprocess.Popen(
        [sys.executable, "-m", "queued_media_downloader", "run", *options],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def wait_for_partial_file(downloads: Path) -> Path:
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        partial_files = [p for p in downloads.rglob("*.part") if p.stat().st_size]
        if partial_files:
            return partial_files[0]
        time.sleep(0.05)
    pytest.fail("The download did not start")


def test_first_ctrl_c_stops_run_leaving_the_job_to_resume(
    local_media_server: str,
    state_directory: Path,
    tmp_path: Path,
    read_stored_job: Callable[[int], Job],
    media_requests: list[tuple[str, str | None]],
) -> None:
    main(["enqueue", f"{local_media_server}/{SLOW_MEDIA_NAME}"])
    run = start_run(state_directory)
    partial_path = wait_for_partial_file(tmp_path / "downloads")

    run.send_signal(signal.SIGINT)
    output, _ = run.communicate(timeout=WAIT_TIMEOUT_SECONDS)

    assert run.returncode == INTERRUPTION_EXIT_CODE
    assert "Interrupted" in output
    assert read_stored_job(1).status is JobStatus.RUNNING
    partial_size = partial_path.stat().st_size
    assert 0 < partial_size < len(SLOW_MEDIA_CONTENT)

    media_requests.clear()
    assert main(["run"]) == 0
    assert read_stored_job(1).status is JobStatus.COMPLETED
    assert (f"/{SLOW_MEDIA_NAME}", f"bytes={partial_size}-") in media_requests


def test_second_ctrl_c_stops_run_at_once(
    local_media_server: str,
    state_directory: Path,
    tmp_path: Path,
    read_stored_job: Callable[[int], Job],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Con un plazo de cancelación largo, solo el segundo Ctrl+C acaba ya.
    monkeypatch.setenv("QUEUED_MEDIA_DOWNLOADER_CANCELLATION_GRACE_SECONDS", "60")
    main(["enqueue", f"{local_media_server}/{SLOW_MEDIA_NAME}"])
    # Sin avances publicados, la cancelación cooperativa no llega a verse.
    monkeypatch.setenv("QUEUED_MEDIA_DOWNLOADER_PROGRESS_INTERVAL_SECONDS", "30")
    run = start_run(state_directory)
    wait_for_partial_file(tmp_path / "downloads")

    run.send_signal(signal.SIGINT)
    time.sleep(0.5)
    run.send_signal(signal.SIGINT)
    started = time.monotonic()
    output, _ = run.communicate(timeout=WAIT_TIMEOUT_SECONDS)

    assert run.returncode == INTERRUPTION_EXIT_CODE
    assert time.monotonic() - started < 15
    assert "Stopped" in output
    assert read_stored_job(1).status is JobStatus.RUNNING


def test_run_keep_waiting_takes_jobs_enqueued_from_another_terminal(
    local_media_server: str,
    state_directory: Path,
    read_stored_job: Callable[[int], Job],
) -> None:
    # UC-03 A5, con dos procesos: run espera y enqueue llega después.
    run = start_run(state_directory, "--keep-waiting")
    time.sleep(1.0)
    assert run.poll() is None

    main(["enqueue", f"{local_media_server}/sample.mp4"])
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if read_stored_job(1).status is JobStatus.COMPLETED:
            break
        time.sleep(0.1)
    still_waiting = run.poll() is None
    run.send_signal(signal.SIGINT)
    output, _ = run.communicate(timeout=WAIT_TIMEOUT_SECONDS)

    assert read_stored_job(1).status is JobStatus.COMPLETED
    assert still_waiting
    assert "Job 1: completed" in output
    assert run.returncode == INTERRUPTION_EXIT_CODE
