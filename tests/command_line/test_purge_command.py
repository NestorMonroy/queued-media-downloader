from pathlib import Path

import pytest

from queued_media_downloader.command_line.command_parser import main


def test_purge_forgets_finished_jobs_and_keeps_their_files(
    local_media_server: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["enqueue", f"{local_media_server}/sample.mp4"])
    main(["enqueue", "https://media.example/watch?v=pending"])
    main(["cancel", "2"])
    main(["run"])
    downloaded = tmp_path / "downloads" / "sample [sample].mp4"
    capsys.readouterr()

    assert main(["purge", "--completed"]) == 0
    assert "Purged 1 job" in capsys.readouterr().out
    main(["list"])
    remaining = capsys.readouterr().out.splitlines()

    assert [line.split()[0] for line in remaining] == ["2"]
    assert downloaded.is_file()


def test_purge_without_options_deletes_completed_and_cancelled(
    local_media_server: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["enqueue", f"{local_media_server}/sample.mp4"])
    main(["enqueue", "https://media.example/watch?v=pending"])
    main(["cancel", "2"])
    main(["run"])
    capsys.readouterr()

    assert main(["purge"]) == 0
    main(["list"])

    assert capsys.readouterr().out.endswith("No jobs\n")
