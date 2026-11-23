import logging
from collections.abc import Callable
from pathlib import Path

import pytest

from queued_media_downloader.command_line import main
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_store import SqliteJobStore
from queued_media_downloader.jobs import (
    FailureReason,
    Job,
    JobId,
    JobKind,
    JobStatus,
)
from tests.command_line.conftest import ENVIRONMENT_PREFIX


def test_enqueue_and_run_download_the_file_and_complete_the_job(
    local_media_server: str,
    tmp_path: Path,
    read_stored_job: Callable[[int], Job],
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["enqueue", f"{local_media_server}/sample.mp4"])

    exit_code = main(["run"])

    output_path = tmp_path / "downloads" / "sample [sample].mp4"
    job = read_stored_job(1)
    assert exit_code == 0
    assert job.status is JobStatus.COMPLETED
    assert job.kind is JobKind.DOWNLOAD
    assert job.output_path == str(output_path)
    assert output_path.read_bytes() == (tmp_path / "served/sample.mp4").read_bytes()
    assert f"Job 1: completed, saved to {output_path}" in capsys.readouterr().out


def test_run_with_a_failed_job_exits_with_code_1(
    local_media_server: str,
    read_stored_job: Callable[[int], Job],
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["enqueue", f"{local_media_server}/missing.mp4"])

    exit_code = main(["run"])

    job = read_stored_job(1)
    assert exit_code == 1
    assert job.status is JobStatus.FAILED
    assert job.failure_reason is FailureReason.UNAVAILABLE
    assert "1 job failed" in capsys.readouterr().out


@pytest.mark.usefixtures("state_directory")
def test_run_with_an_empty_queue_finishes_at_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["run", "--worker-count", "2"])

    assert exit_code == 0
    assert "All jobs finished" in capsys.readouterr().out


@pytest.mark.usefixtures("state_directory")
def test_run_with_an_invalid_worker_count_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["run", "--worker-count", "0"])

    assert exit_code == 2
    assert "worker_count" in capsys.readouterr().err


def test_separate_video_and_audio_are_merged_with_ffmpeg(
    dash_manifest_url: str,
    tmp_path: Path,
    read_stored_job: Callable[[int], Job],
    stream_types: Callable[[Path], list[str]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["enqueue", dash_manifest_url])

    exit_code = main(["run"])

    output_path = tmp_path / "downloads" / "sample [sample].mp4"
    output = capsys.readouterr().out
    assert exit_code == 0
    assert read_stored_job(1).output_path == str(output_path)
    assert stream_types(output_path) == ["audio", "video"]
    # Cuál se usa depende del sistema: la build incluida en Windows, la del PATH
    # en otros sistemas.
    assert any(
        line.startswith("Using ") and ": ffmpeg version " in line
        for line in output.splitlines()
    )
    assert "Copyright" not in output
    assert "Job 1: running Merger" in output


def test_audio_only_keeps_only_the_audio(
    dash_manifest_url: str,
    tmp_path: Path,
    read_stored_job: Callable[[int], Job],
    stream_types: Callable[[Path], list[str]],
) -> None:
    main(["enqueue", dash_manifest_url, "--audio-only"])

    exit_code = main(["run"])

    output_path = tmp_path / "downloads" / "audio" / "sample [sample].m4a"
    assert exit_code == 0
    assert read_stored_job(1).output_path == str(output_path)
    assert stream_types(output_path) == ["audio"]


def test_run_stops_before_any_job_when_ffmpeg_is_not_usable(
    local_media_server: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    read_stored_job: Callable[[int], Job],
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["enqueue", f"{local_media_server}/sample.mp4"])
    monkeypatch.setenv(
        f"{ENVIRONMENT_PREFIX}FFMPEG_PATH", str(tmp_path / "missing-ffmpeg")
    )

    exit_code = main(["run"])

    assert exit_code == 2
    assert "ffmpeg_path" in capsys.readouterr().err
    assert read_stored_job(1).status is JobStatus.PENDING


def test_same_media_with_and_without_audio_only_gives_two_files(
    dash_manifest_url: str,
    tmp_path: Path,
    read_stored_job: Callable[[int], Job],
    stream_types: Callable[[Path], list[str]],
) -> None:
    main(["enqueue", dash_manifest_url])
    main(["enqueue", dash_manifest_url, "--audio-only"])

    exit_code = main(["run"])

    downloads = tmp_path / "downloads"
    assert exit_code == 0
    assert [read_stored_job(job_id).status for job_id in (1, 2)] == [
        JobStatus.COMPLETED,
        JobStatus.COMPLETED,
    ]
    assert stream_types(downloads / "sample [sample].mp4") == ["audio", "video"]
    assert stream_types(downloads / "audio" / "sample [sample].m4a") == ["audio"]


def test_failed_job_shows_its_error_once_and_in_full_in_the_log(
    local_media_server: str,
    state_directory: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    main(["enqueue", f"{local_media_server}/missing.mp4"])

    main(["run"])

    console = capfd.readouterr()
    log_file = state_directory / "logs" / "queued-media-downloader.log"
    assert console.err == ""
    assert console.out.count("HTTP Error 404") == 1
    assert f"See the log for details: {log_file}" in console.out
    assert "HTTP Error 404" in log_file.read_text(encoding="utf-8")


def test_internal_steps_are_hidden_and_logging_is_released(
    local_media_server: str,
    state_directory: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    main(["enqueue", f"{local_media_server}/sample.mp4"])

    main(["run"])

    console = capfd.readouterr()
    assert "MoveFiles" not in console.out
    assert "[download] Download completed" not in console.out
    assert console.err == ""
    log_file = state_directory / "logs" / "queued-media-downloader.log"
    assert "[download] Download completed" in log_file.read_text(encoding="utf-8")
    assert str(log_file) not in {
        getattr(handler, "baseFilename", None)
        for handler in logging.getLogger().handlers
    }


def test_audio_only_never_reuses_or_deletes_the_video_of_another_job(
    webm_dash_manifest_url: str,
    tmp_path: Path,
    read_stored_job: Callable[[int], Job],
    stream_types: Callable[[Path], list[str]],
) -> None:
    # Orden de la evaluación en Windows (T19): el video se une en un .webm y el
    # audio solo, también .webm, se pide después con la misma plantilla.
    main(["enqueue", webm_dash_manifest_url])
    main(["enqueue", webm_dash_manifest_url, "--audio-only"])

    exit_code = main(["run"])

    video_path = tmp_path / "downloads" / "sample [sample].webm"
    audio_path = tmp_path / "downloads" / "audio" / "sample [sample].opus"
    assert exit_code == 0
    assert read_stored_job(1).output_path == str(video_path)
    assert read_stored_job(2).output_path == str(audio_path)
    assert stream_types(video_path) == ["audio", "video"]
    assert stream_types(audio_path) == ["audio"]


@pytest.mark.parametrize("worker_count", ["1", "2"])
def test_enqueue_and_run_download_a_playlist_into_its_folder(
    worker_count: str,
    local_media_server: str,
    tmp_path: Path,
    read_stored_job: Callable[[int], Job],
    capsys: pytest.CaptureFixture[str],
) -> None:
    # feed.xml: Video A (sample.mp4), Video B (other.mp4) y una lista anidada
    # cuya única entrada vuelve a ser other.mp4.
    main(["enqueue", f"{local_media_server}/feed.xml"])

    exit_code = main(["run", "--worker-count", worker_count])

    downloads = tmp_path / "downloads"
    assert exit_code == 0
    assert (downloads / "Local feed" / "1 - sample [sample].mp4").is_file()
    # other.mp4 está en las dos listas y se descarga una sola vez. Con varios
    # workers, la copia que se queda es la del primer job que lo encuentra.
    other_files = [
        path for path in downloads.rglob("*.mp4") if path.name.endswith("other].mp4")
    ]
    assert [path.relative_to(downloads) for path in other_files] in (
        [Path("Local feed", "2 - other [other].mp4")],
        [Path("Nested feed", "1 - other [other].mp4")],
    )
    playlist_job = read_stored_job(1)
    assert playlist_job.kind is JobKind.EXPANSION
    assert playlist_job.status is JobStatus.COMPLETED
    assert read_stored_job(5).parent_id == 4
    other_statuses = {read_stored_job(job_id).status for job_id in (3, 5)}
    assert other_statuses == {JobStatus.COMPLETED, JobStatus.SKIPPED}
    output = capsys.readouterr().out
    assert "Job 1: found 3 entries in playlist 'Local feed'" in output
    assert "Job 4: found 1 entry in playlist 'Nested feed'" in output


def test_run_recovers_a_job_left_running_and_finishes_it(
    local_media_server: str,
    state_directory: Path,
    read_stored_job: Callable[[int], Job],
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["enqueue", f"{local_media_server}/sample.mp4"])
    # Un run anterior se cerró a la fuerza con el job en curso.
    connection = open_database(state_directory / "queue.sqlite3")
    try:
        job_store = SqliteJobStore(connection)
        job_store.update(job_store.get(JobId(1)).start())
    finally:
        connection.close()

    exit_code = main(["run"])

    assert exit_code == 0
    assert read_stored_job(1).status is JobStatus.COMPLETED
    assert "Recovered 1 interrupted job" in capsys.readouterr().out


def test_run_without_interrupted_jobs_does_not_mention_recovery(
    local_media_server: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["enqueue", f"{local_media_server}/sample.mp4"])

    main(["run"])

    assert "Recovered" not in capsys.readouterr().out
