import subprocess
import sys

import pytest

from queued_media_downloader.command_line import main

EXPECTED_VERSION_LINE = "queued-media-downloader 0.1.0"


def test_version_option_prints_distribution_name_and_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["--version"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == EXPECTED_VERSION_LINE


def test_package_runs_as_module_through_its_entry_point() -> None:
    completed_process = subprocess.run(
        [sys.executable, "-m", "queued_media_downloader", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed_process.returncode == 0
    assert completed_process.stdout.strip() == EXPECTED_VERSION_LINE
