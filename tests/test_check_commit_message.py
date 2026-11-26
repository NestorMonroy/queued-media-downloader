import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "check_commit_message.py"
VALID_MESSAGE = "Claim each final name before downloading\n\nBody line.\n"


def check(message: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    message_file = tmp_path / "message.txt"
    message_file.write_text(message, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(message_file)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_a_message_that_follows_the_conventions_passes(tmp_path: Path) -> None:
    result = check(VALID_MESSAGE, tmp_path)

    assert result.returncode == 0
    assert result.stdout.strip().endswith(": OK")


@pytest.mark.parametrize(
    ("message", "problem"),
    [
        ("A" * 51 + "\n\nBody.\n", "subject has 51 characters"),
        ("lowercase subject\n\nBody.\n", "not capitalized"),
        ("Ends with a period.\n\nBody.\n", "ends with a period"),
        ("Subject\nBody without a blank line\n", "no blank line"),
        ("Subject\n\n" + "b" * 73 + "\n", "body lines over 72 characters: [3]"),
    ],
)
def test_each_broken_rule_is_reported_with_exit_code_1(
    tmp_path: Path, message: str, problem: str
) -> None:
    result = check(message, tmp_path)

    assert result.returncode == 1
    assert problem in result.stdout
