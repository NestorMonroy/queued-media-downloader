"""Pruebas negativas de stop-on-error en commits, comprobaciones y publicación.

Cada prueba trabaja en un repositorio temporal con un remoto desnudo local y un
`scripts/run_checks.py` sustituto cuyo código de salida decide la prueba; nunca
toca el repositorio del proyecto ni su remoto.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
VALID = "Add the first file\n\nExplain why the file exists.\n"
INVALID = "add the first file.\n\nExplain why.\n"
STUB_CHECKS = """import sys
from pathlib import Path
exit_file = Path("checks_exit_code")
code = int(exit_file.read_text()) if exit_file.exists() else 0
Path("checks_ran").write_text("yes")
for number in range(5000):
    print(f"line {number} of a long verification output")
sys.exit(code)
"""

pytestmark = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("git", "git-lfs", "uv", "sh")),
    reason="needs git, git-lfs, uv and sh",
)


def clean_environment() -> dict[str, str]:
    """Entorno sin variables GIT_* heredadas y con una identidad de prueba."""
    environment = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    for role in ("AUTHOR", "COMMITTER"):
        environment[f"GIT_{role}_NAME"] = "Test"
        environment[f"GIT_{role}_EMAIL"] = "test@example.invalid"
    return environment


def run(
    repository: Path, *command: str, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Ejecuta un comando en el repositorio temporal sin enmascarar su código."""
    return subprocess.run(
        command,
        cwd=repository,
        env=clean_environment(),
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def head(repository: Path, reference: str = "HEAD") -> str:
    """SHA de una referencia, o cadena vacía si no existe."""
    result = run(repository, "git", "rev-parse", "--verify", "--quiet", reference)
    return result.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Clon de trabajo con los hooks instalados y un remoto desnudo `origin`."""
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(remote)],
        check=True,
        env=clean_environment(),
    )
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(work)],
        check=True,
        env=clean_environment(),
    )
    (work / "scripts" / "hooks").mkdir(parents=True)
    for name in ("git_hooks.py", "check_commit_message.py"):
        shutil.copy(SCRIPTS / name, work / "scripts" / name)
    for name in ("commit-msg", "pre-push"):
        shutil.copy(SCRIPTS / "hooks" / name, work / "scripts" / "hooks" / name)
    (work / "scripts" / "run_checks.py").write_text(STUB_CHECKS, encoding="utf-8")
    (work / ".gitignore").write_text("checks_exit_code\nchecks_ran\n", encoding="utf-8")
    installed = run(work, sys.executable, "-m", "scripts.git_hooks", "install")
    assert installed.returncode == 0, installed.stdout + installed.stderr
    assert run(work, "git", "remote", "add", "origin", str(remote)).returncode == 0
    assert run(work, "git", "add", ".").returncode == 0
    first = run(
        work, "git", "commit", "-q", "-m", "Add the project scripts", "-m", "Body."
    )
    assert first.returncode == 0, first.stdout + first.stderr
    return work


def commit_file(
    repository: Path, name: str, message: str
) -> subprocess.CompletedProcess[str]:
    """Añade un archivo y lo confirma con el mensaje indicado."""
    (repository / name).write_text(name, encoding="utf-8")
    run(repository, "git", "add", name)
    message_file = repository.parent / "message.txt"
    message_file.write_text(message, encoding="utf-8")
    return run(repository, "git", "commit", "-q", "-F", str(message_file))


def test_an_invalid_message_creates_no_commit(repository: Path) -> None:
    before = head(repository)

    result = commit_file(repository, "a.txt", INVALID)

    assert result.returncode != 0
    assert "commit rejected" in result.stdout + result.stderr
    assert head(repository) == before


def test_a_valid_message_creates_the_commit(repository: Path) -> None:
    before = head(repository)

    result = commit_file(repository, "a.txt", VALID)

    assert result.returncode == 0, result.stdout + result.stderr
    assert head(repository) != before


def test_editor_comments_are_ignored_as_git_strips_them(repository: Path) -> None:
    editor = repository.parent / "editor.sh"
    editor.write_text(
        "#!/bin/sh\n{ printf 'Add from the editor\\n\\nBody.\\n'; cat \"$1\"; }"
        ' > "$1.new" && mv "$1.new" "$1"\n',
        encoding="utf-8",
    )
    editor.chmod(0o755)
    (repository / "a.txt").write_text("a", encoding="utf-8")
    run(repository, "git", "add", "a.txt")
    environment = clean_environment() | {"GIT_EDITOR": str(editor)}

    result = subprocess.run(
        ["git", "commit", "-q", "-v"],
        cwd=repository,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_a_failing_gate_stops_the_push_and_keeps_its_exit_code(
    repository: Path,
) -> None:
    (repository / "checks_exit_code").write_text("5", encoding="utf-8")

    result = run(repository, "git", "push", "-q", "origin", "main")

    assert result.returncode != 0
    assert "run_checks.py exited with 5" in result.stdout + result.stderr
    assert head(repository, "refs/remotes/origin/main") == ""
    remote = run(repository, "git", "ls-remote", "origin", "main")
    assert remote.stdout == ""


def test_a_commit_that_skipped_the_hook_cannot_be_published(repository: Path) -> None:
    (repository / "b.txt").write_text("b", encoding="utf-8")
    run(repository, "git", "add", "b.txt")
    skipped = run(
        repository, "git", "commit", "-q", "--no-verify", "-m", "bad subject."
    )
    assert skipped.returncode == 0

    result = run(repository, "git", "push", "-q", "origin", "main")

    assert result.returncode != 0
    assert "push rejected" in result.stdout
    assert not (repository / "checks_ran").exists()
    assert run(repository, "git", "ls-remote", "origin", "main").stdout == ""


def test_uncommitted_changes_block_publication(repository: Path) -> None:
    (repository / ".gitignore").write_text("changed\n", encoding="utf-8")

    result = run(repository, "git", "push", "-q", "origin", "main")

    assert result.returncode != 0
    assert "working tree has changes" in result.stdout
    assert run(repository, "git", "ls-remote", "origin", "main").stdout == ""


def test_publishing_a_commit_other_than_head_is_refused(repository: Path) -> None:
    first = head(repository)
    assert commit_file(repository, "a.txt", VALID).returncode == 0

    result = run(repository, "git", "push", "-q", "origin", f"{first}:refs/heads/main")

    assert result.returncode != 0
    assert "check out the commit you publish" in result.stdout


def test_passing_checks_allow_the_push(repository: Path) -> None:
    result = run(repository, "git", "push", "-q", "origin", "main")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (repository / "checks_ran").exists()
    remote = run(repository, "git", "ls-remote", "origin", "main").stdout.split()
    assert remote[0] == head(repository)


def test_the_check_command_reports_missing_hooks(repository: Path) -> None:
    assert (
        run(repository, sys.executable, "-m", "scripts.git_hooks", "check").returncode
        == 0
    )
    (repository / ".git" / "hooks" / "commit-msg").unlink()

    result = run(repository, sys.executable, "-m", "scripts.git_hooks", "check")

    assert result.returncode == 1
    assert "commit-msg" in result.stdout


def test_install_keeps_a_foreign_hook(repository: Path) -> None:
    foreign = repository / ".git" / "hooks" / "commit-msg"
    foreign.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    result = run(repository, sys.executable, "-m", "scripts.git_hooks", "install")

    assert result.returncode == 1
    assert foreign.read_text(encoding="utf-8") == "#!/bin/sh\nexit 0\n"


def test_run_checks_stops_at_the_first_failure_with_its_code(tmp_path: Path) -> None:
    driver = tmp_path / "driver.py"
    marker = tmp_path / "second_ran"
    failing = "import sys; print('x' * 100000); sys.exit(4)"
    second = f"open({str(marker)!r}, 'w')"
    driver.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
        "import run_checks\n"
        "run_checks.CHECKS = (\n"
        f"    ('first', [sys.executable, '-c', {failing!r}]),\n"
        f"    ('second', [sys.executable, '-c', {second!r}]),\n"
        ")\n"
        "sys.exit(run_checks.main())\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(driver)], capture_output=True, text=True, check=False
    )

    assert result.returncode == 4
    assert "not run (stop-on-error): second" in result.stdout
    assert not marker.exists()
