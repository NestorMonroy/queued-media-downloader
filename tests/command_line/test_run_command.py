from collections.abc import Callable
from pathlib import Path

import pytest

from queued_media_downloader.command_line import main
from queued_media_downloader.jobs import FailureReason, Job, JobKind, JobStatus
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
    assert "Using ffmpeg" in output
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

    output_path = tmp_path / "downloads" / "sample [sample].m4a"
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
    assert stream_types(downloads / "sample [sample].m4a") == ["audio"]
