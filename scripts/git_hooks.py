"""Hooks de Git del proyecto: mensaje de commit y publicación con stop-on-error.

Git no instala hooks al clonar, así que cada clon los instala una vez:

    uv run python -m scripts.git_hooks install   # copia scripts/hooks/*
    uv run python -m scripts.git_hooks check     # 0 si están instalados

Se ejecuta como módulo desde la raíz del repositorio, para que la importación
de `scripts.check_commit_message` sea la misma en ejecución y para mypy.

Los envoltorios de `scripts/hooks/` llaman a este módulo:

- `commit-msg FILE`: aplica `check_commit_message.py` al mensaje tal como Git
  lo guardará (sin las líneas de comentario ni la diferencia tras la línea de
  tijera). Un mensaje inválido termina con 1 y Git no crea el commit.
- `pre-push REMOTE URL` (las referencias llegan por la entrada estándar):
  rechaza la publicación si un commit nuevo tiene un mensaje inválido, si lo
  publicado no es el HEAD que se verifica, si el árbol de trabajo tiene
  cambios, o si `run_checks.py` falla. Devuelve el código real del fallo.

El envoltorio de `pre-push` encadena después el hook de Git LFS, que el
repositorio necesita para los binarios de ffmpeg.
"""

import os
import subprocess
import sys
from pathlib import Path

from scripts.check_commit_message import commit_message_problems

HOOK_NAMES = ("commit-msg", "pre-push")
HOOK_SOURCES = Path(__file__).parent / "hooks"
HOOK_MARKER = "queued-media-downloader git hook"
LFS_STUB_MARKER = "This repository is configured for Git LFS"
ZERO_SHA = "0" * 40
SCISSORS = "------------------------ >8 ------------------------"


def git(*arguments: str) -> str:
    """Salida de un comando de Git; un fallo de Git se propaga como excepción."""
    return subprocess.run(
        ["git", *arguments], check=True, capture_output=True, text=True
    ).stdout


def comment_char() -> str:
    """Carácter de comentario de Git (`core.commentChar`; `auto` usa `#`)."""
    configured = subprocess.run(
        ["git", "config", "--get", "core.commentChar"],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return configured if configured and configured != "auto" else "#"


def message_as_committed(text: str, comment: str) -> str:
    """Mensaje sin la diferencia tras la tijera ni las líneas de comentario."""
    kept: list[str] = []
    for line in text.split("\n"):
        if line == f"{comment} {SCISSORS}":
            break
        if not line.startswith(comment):
            kept.append(line.rstrip())
    return "\n".join(kept).strip("\n") + "\n"


def commit_msg(path: Path) -> int:
    """Hook commit-msg: 0 si el mensaje cumple las convenciones; 1 si no."""
    message = message_as_committed(path.read_text(encoding="utf-8"), comment_char())
    problems = commit_message_problems(message)
    subject = message.split("\n", 1)[0]
    if problems:
        print(f"commit rejected: [{len(subject)}] {subject}: {'; '.join(problems)}")
        return 1
    return 0


def pushed_updates(lines: list[str]) -> list[tuple[str, str]]:
    """Pares (sha local, referencia remota) de las referencias que se publican."""
    updates = []
    for line in lines:
        fields = line.split()
        if len(fields) == 4 and fields[1] != ZERO_SHA:
            updates.append((fields[1], fields[2]))
    return updates


def push_problems(remote: str, updates: list[tuple[str, str]]) -> list[str]:
    """Condiciones que impiden publicar, antes de ejecutar las comprobaciones."""
    problems = []
    head = git("rev-parse", "HEAD").strip()
    for local_sha, remote_ref in updates:
        if local_sha != head:
            problems.append(
                f"{remote_ref}: pushes {local_sha[:7]}, but the checks run on"
                f" HEAD {head[:7]}; check out the commit you publish"
            )
        new_commits = git("rev-list", local_sha, "--not", f"--remotes={remote}").split()
        for commit in new_commits:
            message = git("log", "-1", "--format=%B", commit)
            found = commit_message_problems(message)
            if found:
                problems.append(f"commit {commit[:7]}: {'; '.join(found)}")
    if git("status", "--porcelain"):
        problems.append(
            "the working tree has changes; the checks would not verify HEAD"
        )
    return problems


def without_git_variables() -> dict[str, str]:
    """Entorno sin las variables GIT_* que Git exporta a sus hooks."""
    return {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }


def pre_push(remote: str, lines: list[str]) -> int:
    """Hook pre-push: 0 si se puede publicar; si no, el código del fallo."""
    updates = pushed_updates(lines)
    if not updates:
        return 0
    problems = push_problems(remote, updates)
    if problems:
        print("push rejected:")
        print("\n".join(f"  - {problem}" for problem in problems))
        return 1
    checks = subprocess.run(
        [sys.executable, "scripts/run_checks.py"],
        check=False,
        env=without_git_variables(),
    )
    if checks.returncode != 0:
        print(f"push rejected: scripts/run_checks.py exited with {checks.returncode}")
    return checks.returncode


def hooks_directory() -> Path:
    """Directorio de hooks que Git usa (respeta `core.hooksPath`)."""
    return Path(git("rev-parse", "--git-path", "hooks").strip())


def install() -> int:
    """Copia los hooks; no sobrescribe un hook ajeno salvo el stub de Git LFS."""
    target = hooks_directory()
    target.mkdir(parents=True, exist_ok=True)
    refused = []
    for name in HOOK_NAMES:
        source = (HOOK_SOURCES / name).read_text(encoding="utf-8")
        destination = target / name
        if destination.exists():
            current = destination.read_text(encoding="utf-8", errors="replace")
            if HOOK_MARKER not in current and LFS_STUB_MARKER not in current:
                refused.append(str(destination))
                continue
        destination.write_text(source, encoding="utf-8", newline="\n")
        destination.chmod(0o755)
        print(f"installed {destination}")
    for path in refused:
        print(f"not replaced (foreign hook, merge it by hand): {path}")
    return 1 if refused else 0


def check_installed() -> int:
    """0 si los hooks instalados coinciden con los del repositorio; 1 si no."""
    target = hooks_directory()
    stale = [
        name
        for name in HOOK_NAMES
        if not (target / name).exists()
        or (target / name).read_text(encoding="utf-8", errors="replace")
        != (HOOK_SOURCES / name).read_text(encoding="utf-8")
    ]
    if stale:
        print(f"hooks missing or outdated: {', '.join(stale)}; run 'install'")
        return 1
    print("hooks installed")
    return 0


def main() -> int:
    """Despacha el subcomando y devuelve su código de salida."""
    match sys.argv[1:]:
        case ["commit-msg", path]:
            return commit_msg(Path(path))
        case ["pre-push", remote, _url]:
            return pre_push(remote, sys.stdin.read().splitlines())
        case ["install"]:
            return install()
        case ["check"]:
            return check_installed()
    print(
        "usage: python -m scripts.git_hooks"
        " commit-msg FILE | pre-push REMOTE URL | install | check",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
