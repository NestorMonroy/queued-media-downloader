"""run cuando un worker no se puede registrar en su terminador (T42, Windows).

En Windows, un worker que muere mientras se asocia a su Job Object hace
fallar su registro. Aquí se simula con FakeProcessTreeTerminator: el
comportamiento nativo de Windows se valida en la campaña.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from queued_media_downloader.command_line import composition_root
from queued_media_downloader.command_line.command_parser import main
from queued_media_downloader.jobs import Job, JobStatus
from queued_media_downloader.workers import ProcessTreeTerminationError
from queued_media_downloader.workers.process_worker_pool import ProcessWorkerPool
from tests.doubles.fake_process_tree_terminator import FakeProcessTreeTerminator


def test_workers_that_never_register_stop_run_without_a_trace(
    local_media_server: str,
    read_stored_job: Callable[[int], Job],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main(["enqueue", f"{local_media_server}/sample.mp4"])
    monkeypatch.setattr(
        composition_root,
        "create_process_tree_terminator",
        lambda: FakeProcessTreeTerminator(fail_registration=True),
    )
    capsys.readouterr()

    exit_code = main(["run"])

    error = capsys.readouterr().err
    assert exit_code == 1
    assert "could not start a worker" in error
    assert "Traceback" not in error
    assert read_stored_job(1).status is JobStatus.PENDING


def test_a_replacement_that_fails_mid_run_stops_every_worker_at_once(
    local_media_server: str,
    state_directory: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del state_directory
    main(["enqueue", f"{local_media_server}/sample.mp4"])
    shutdowns: list[bool] = []
    real_shut_down = ProcessWorkerPool.shut_down

    def recording_shut_down(
        pool: ProcessWorkerPool, *, immediately: bool = False
    ) -> None:
        shutdowns.append(immediately)
        real_shut_down(pool, immediately=immediately)

    def fail_to_replace(
        self: ProcessWorkerPool, timeout_seconds: float
    ) -> list[object]:
        del self, timeout_seconds
        message = "Scripted registration failure of a replacement"
        raise ProcessTreeTerminationError(message)

    monkeypatch.setattr(ProcessWorkerPool, "shut_down", recording_shut_down)
    monkeypatch.setattr(ProcessWorkerPool, "collect_events", fail_to_replace)
    capsys.readouterr()

    exit_code = main(["run"])

    assert exit_code == 1
    assert "could not start a worker" in capsys.readouterr().err
    assert shutdowns[0] is True
