from pathlib import Path

import pytest

from queued_media_downloader.command_line import main
from queued_media_downloader.job_storage.sqlite_migrations import LATEST_SCHEMA_VERSION
from tests.command_line.conftest import ENVIRONMENT_PREFIX


@pytest.mark.usefixtures("state_directory")
def test_diagnose_reports_every_component_and_exits_with_0(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["diagnose"])

    output = capsys.readouterr().out
    assert exit_code == 0
    for component in ("ffmpeg", "ffprobe", "deno", "database"):
        assert f"] {component}: " in output
    assert f"schema version {LATEST_SCHEMA_VERSION}" in output
    assert output.endswith("Environment ready\n")


@pytest.mark.usefixtures("state_directory")
def test_diagnose_with_unusable_ffmpeg_exits_with_2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(
        f"{ENVIRONMENT_PREFIX}FFMPEG_PATH", str(tmp_path / "missing-ffmpeg")
    )

    exit_code = main(["diagnose"])

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "[FAIL] ffmpeg: ffmpeg_path points to" in output
    assert "[ OK ] deno: " in output
    assert output.endswith("1 check failed\n")


@pytest.mark.usefixtures("state_directory")
def test_diagnose_with_invalid_settings_exits_with_2(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(f"{ENVIRONMENT_PREFIX}WORKER_COUNT", "0")

    exit_code = main(["diagnose"])

    assert exit_code == 2
    assert "worker_count" in capsys.readouterr().err
