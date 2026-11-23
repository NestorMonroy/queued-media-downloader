from collections.abc import Iterator
from pathlib import Path

import pytest

from queued_media_downloader.command_line import main
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_store import SqliteJobStore
from queued_media_downloader.jobs import DownloadOptions, Job, JobKind, JobStatus
from tests.command_line.conftest import ENVIRONMENT_PREFIX


def stored_jobs(state_directory: Path) -> Iterator[Job]:
    """Lee los jobs pendientes que dejó el comando en la base de datos."""
    database_path = state_directory / "queue.sqlite3"
    if not database_path.exists():
        return
    connection = open_database(database_path)
    try:
        yield from SqliteJobStore(connection).get_next_pending(limit=10)
    finally:
        connection.close()


def test_enqueue_stores_pending_expansion_job_and_reports_its_id(
    state_directory: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["enqueue", "https://example.com/watch?v=1"])

    [job] = stored_jobs(state_directory)
    assert exit_code == 0
    assert capsys.readouterr().out == f"Queued job {job.job_id}\n"
    assert job.kind is JobKind.EXPANSION
    assert job.status is JobStatus.PENDING
    assert job.download_options == DownloadOptions(
        format_selector="bv*+ba/b",
        download_directory=tmp_path / "downloads",
        output_template="%(title)s [%(id)s].%(ext)s",
        audio_only=False,
    )


def test_enqueue_options_override_the_configuration(
    state_directory: Path, tmp_path: Path
) -> None:
    exit_code = main(
        [
            "enqueue",
            "https://example.com/a",
            "https://example.com/b",
            "--format",
            "bestaudio",
            "--audio-only",
            "--download-directory",
            str(tmp_path / "music"),
        ]
    )

    jobs = list(stored_jobs(state_directory))
    assert exit_code == 0
    assert [job.url for job in jobs] == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    for job in jobs:
        assert job.download_options.format_selector == "bestaudio"
        assert job.download_options.audio_only is True
        assert job.download_options.download_directory == tmp_path / "music"


def test_enqueue_with_invalid_url_names_it_and_stores_nothing(
    state_directory: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["enqueue", "https://example.com/valid", "not a url"])

    assert exit_code == 2
    assert "'not a url'" in capsys.readouterr().err
    assert list(stored_jobs(state_directory)) == []


def test_enqueue_with_invalid_setting_names_it_and_stores_nothing(
    state_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(f"{ENVIRONMENT_PREFIX}WORKER_COUNT", "0")

    exit_code = main(["enqueue", "https://example.com/valid"])

    assert exit_code == 2
    assert "worker_count" in capsys.readouterr().err
    assert list(stored_jobs(state_directory)) == []


@pytest.mark.usefixtures("state_directory")
def test_enqueue_without_url_is_a_usage_error() -> None:
    assert main(["enqueue"]) == 2


def test_audio_only_without_format_selects_the_best_audio(
    state_directory: Path,
) -> None:
    exit_code = main(["enqueue", "https://example.com/a", "--audio-only"])

    [job] = stored_jobs(state_directory)
    assert exit_code == 0
    assert job.download_options.audio_only is True
    assert job.download_options.format_selector == "ba/b"
