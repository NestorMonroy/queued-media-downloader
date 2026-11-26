"""Ejecuta las cinco verificaciones del proyecto, en orden y con stop-on-error.

Cada verificación conserva su salida completa y su código de salida. Si una
falla, las siguientes no se ejecutan y el script termina con ese código, para
corregir la causa antes de seguir (sin commits, merges ni publicaciones).

Uso, desde la raíz del repositorio (Linux o Windows):

    uv run python scripts/run_checks.py            # las cinco
    uv run python scripts/run_checks.py -- -m windows   # argumentos para pytest
"""

import subprocess
import sys
import time

CHECKS: tuple[tuple[str, list[str]], ...] = (
    ("format", ["ruff", "format", "--check", "."]),
    ("lint", ["ruff", "check", "."]),
    ("types", ["mypy"]),
    ("architecture", ["lint-imports"]),
    ("tests", ["pytest"]),
)


def main() -> int:
    """Ejecuta las verificaciones y devuelve el código de la primera que falle."""
    pytest_arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    results: list[tuple[str, int, float]] = []
    for name, command in CHECKS:
        if name == "tests":
            command = [*command, *pytest_arguments]
        print(f"\n=== {name}: {' '.join(command)}", flush=True)
        started = time.monotonic()
        return_code = subprocess.run(command, check=False).returncode
        results.append((name, return_code, time.monotonic() - started))
        if return_code != 0:
            break
    print("\n=== summary")
    for name, return_code, seconds in results:
        verdict = "PASSED" if return_code == 0 else f"FAILED (exit code {return_code})"
        print(f"{name:<13} {verdict:<26} {seconds:6.1f} s")
    skipped = [name for name, _ in CHECKS[len(results) :]]
    if skipped:
        print(f"not run (stop-on-error): {', '.join(skipped)}")
    return next((code for _, code, _ in results if code != 0), 0)


if __name__ == "__main__":
    sys.exit(main())
