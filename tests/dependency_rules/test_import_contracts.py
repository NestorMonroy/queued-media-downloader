import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "queued_media_downloader"
LINT_IMPORTS = Path(sys.executable).with_name("lint-imports")


def copy_package_with_module(
    destination: Path, module_path: str, module_source: str
) -> Path:
    """Copia el paquete en destination y añade un módulo extra a la copia."""
    package_copy = destination / PACKAGE_NAME
    shutil.copytree(
        PROJECT_ROOT / PACKAGE_NAME,
        package_copy,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    extra_module = package_copy / module_path
    extra_module.write_text(module_source, encoding="utf-8")
    return destination


def run_import_contracts(package_parent: Path) -> subprocess.CompletedProcess[str]:
    """Ejecuta lint-imports con la configuración del proyecto sobre una copia."""
    return subprocess.run(
        [
            str(LINT_IMPORTS),
            "--config",
            str(PROJECT_ROOT / "pyproject.toml"),
            "--no-cache",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=package_parent,
        # Se conserva el entorno (Windows necesita SYSTEMROOT, entre otras);
        # PYTHONPATH hace que se analice la copia y no el paquete instalado.
        env={**os.environ, "PYTHONPATH": str(package_parent)},
    )


def test_package_without_violations_keeps_every_contract(tmp_path: Path) -> None:
    package_parent = copy_package_with_module(
        tmp_path, "jobs/harmless_module.py", '"""Módulo sin imports."""\n'
    )

    lint_result = run_import_contracts(package_parent)

    assert lint_result.returncode == 0, lint_result.stdout


@pytest.mark.parametrize(
    ("module_path", "module_source", "broken_contract"),
    [
        pytest.param(
            "jobs/upward_import.py",
            "import queued_media_downloader.job_queue\n",
            "Components only depend on lower components",
            id="lower component imports a higher one",
        ),
        pytest.param(
            "job_queue/internal_import.py",
            "import queued_media_downloader.job_storage.internal_module\n",
            "job_storage is only used through its public API",
            id="component imports an internal module of another",
        ),
        pytest.param(
            "command_line/internal_import.py",
            "import queued_media_downloader.job_storage.internal_module\n",
            "job_storage is only used through its public API",
            id="command_line outside composition_root imports an internal module",
        ),
        pytest.param(
            "workers/yt_dlp_import.py",
            "import yt_dlp\n",
            "Only media_extraction imports yt_dlp",
            id="yt_dlp imported outside media_extraction",
        ),
    ],
)
def test_forbidden_import_breaks_its_contract(
    tmp_path: Path, module_path: str, module_source: str, broken_contract: str
) -> None:
    package_parent = copy_package_with_module(tmp_path, module_path, module_source)
    internal_module = package_parent / PACKAGE_NAME / "job_storage/internal_module.py"
    internal_module.write_text('"""Módulo interno."""\n', encoding="utf-8")

    lint_result = run_import_contracts(package_parent)

    assert lint_result.returncode != 0
    assert f"{broken_contract} BROKEN" in lint_result.stdout
