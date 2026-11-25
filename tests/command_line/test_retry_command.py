from collections.abc import Callable
from pathlib import Path

import pytest

from queued_media_downloader.command_line.command_parser import main
from queued_media_downloader.jobs import Job, JobStatus


def test_failed_job_is_retried_by_the_next_run(
    local_media_server: str,
    tmp_path: Path,
    read_stored_job: Callable[[int], Job],
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Un job que falla (404) y que, cuando el contenido ya existe, se reintenta.
    main(["enqueue", f"{local_media_server}/late.mp4"])
    assert main(["run"]) == 1
    served = tmp_path / "served"
    (served / "late.mp4").write_bytes((served / "sample.mp4").read_bytes())
    capsys.readouterr()

    assert main(["retry", "1"]) == 0
    assert "Retry requested for job 1" in capsys.readouterr().out
    assert read_stored_job(1).status is JobStatus.FAILED

    assert main(["run"]) == 0
    retried = read_stored_job(1)
    assert retried.status is JobStatus.COMPLETED
    assert retried.attempt_count == 1
    assert "Job 1: queued again (attempt 2)" in capsys.readouterr().out


def test_completed_job_is_not_retried(
    local_media_server: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["enqueue", f"{local_media_server}/sample.mp4"])
    main(["run"])
    capsys.readouterr()

    assert main(["retry", "1"]) == 0
    assert "Job 1 is COMPLETED; only FAILED or CANCELLED" in capsys.readouterr().out


def test_retry_needs_job_ids_or_all_failed() -> None:
    assert main(["retry"]) == 2
