import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "check_requirements_model.py"

USE_CASE = """# UC-01: Encolar

- **Estado:** aprobado; implementado.

## Flujos alternativos

- **A1. Uno vigente:** con los valores por defecto.
- **A2. Otro propuesto** (propuesto): según [BR-01](../business-rules.md).

## Excepciones

- **E1. Uno defectuoso:** **Defecto (R-01):** falla mal.

## Criterios de aceptación

1. Funciona.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Uno | **Windows** |
"""


def load_script() -> ModuleType:
    specification = importlib.util.spec_from_file_location("check_model", SCRIPT)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    write(
        tmp_path / "README.md",
        "# Proyecto\n\n[Modelo](doc/requirements/use-case-model.md)\n",
    )
    write(tmp_path / "doc/requirements/use-cases/uc-01-enqueue.md", USE_CASE)
    write(
        tmp_path / "doc/requirements/use-case-model.md",
        "# Modelo\n\n## Casos de uso\n\n| UC-01 | Encolar |\n\n"
        "<!-- completeness-matrix:start -->\n<!-- completeness-matrix:end -->\n",
    )
    write(
        tmp_path / "doc/requirements/business-rules.md",
        "# Reglas\n\n| BR-01 | C | Regla |\n",
    )
    write(
        tmp_path / "doc/requirements/supplementary-specification.md",
        "# Suplementarios\n\n| SUP-F01 | Salida |\n",
    )
    write(
        tmp_path / "doc/requirements/requirements-analysis.md",
        "# Análisis\n\n### D-1. Algo\n",
    )
    write(
        tmp_path / "doc/project-management/risk-list.md",
        "# Riesgos\n\n| R-01 | Riesgo |\n",
    )
    subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--write"],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return tmp_path


def check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_a_coherent_model_passes(repository: Path) -> None:
    result = check(repository)

    assert result.returncode == 0, result.stdout
    assert result.stdout.strip().endswith("requirements model: OK")


def test_the_generated_matrix_counts_flows_by_state(repository: Path) -> None:
    model = (repository / "doc/requirements/use-case-model.md").read_text("utf-8")

    assert (
        "| UC-01 | aprobado | 2 | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 1 | Sí |"
        in model
    )


def test_a_broken_link_fails(repository: Path) -> None:
    write(repository / "doc/notes.md", "[Falta](missing.md) y [ancla](notes.md#nope)\n")

    result = check(repository)

    assert result.returncode == 1
    assert "doc/notes.md: missing missing.md" in result.stdout
    assert "doc/notes.md: missing anchor notes.md#nope" in result.stdout


def test_a_broken_link_in_third_party_material_is_reported_but_does_not_fail(
    repository: Path,
) -> None:
    write(repository / "doc/reference/guide.md", "[Falta](/glossary/case.md)\n")

    result = check(repository)

    assert result.returncode == 0
    assert "third-party (not modified, not failing): 1" in result.stdout


@pytest.mark.parametrize("reference", ["BR-07", "SUP-X09", "D-9", "R-55", "UC-44"])
def test_an_undefined_identifier_fails(repository: Path, reference: str) -> None:
    write(repository / "doc/notes.md", f"Ver {reference}.\n")

    result = check(repository)

    assert result.returncode == 1
    assert f"undefined {reference}" in result.stdout


def test_audit_findings_are_not_taken_for_decisions(repository: Path) -> None:
    write(repository / "doc/notes.md", "Hallazgo D-01 de la auditoría.\n")

    assert check(repository).returncode == 0


def test_an_outdated_matrix_fails_until_it_is_regenerated(repository: Path) -> None:
    use_case = repository / "doc/requirements/use-cases/uc-01-enqueue.md"
    use_case.write_text(
        USE_CASE.replace(
            "## Excepciones", "- **A3. Nuevo** (propuesto).\n\n## Excepciones"
        ),
        encoding="utf-8",
    )

    assert check(repository).returncode == 1
    subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(repository), "--write"],
        check=True,
        capture_output=True,
        timeout=60,
    )
    assert check(repository).returncode == 0


@pytest.mark.parametrize(
    ("text", "state"),
    [
        ("con los valores por defecto", "implementado"),
        ("**Defecto (R-28):** falla", "defecto"),
        ("**Divergencia hoy:** 0 reintentos", "divergente"),
        ("(**sin cualificar**, D-10)", "sin cualificar"),
        ("(condicionado a D-1)", "condicionado"),
        ("**Limitación:** la identidad", "parcial"),
        ("(propuesto, prioridad baja)", "propuesto"),
    ],
)
def test_flow_state_follows_its_marks(text: str, state: str) -> None:
    assert load_script().flow_state(text) == state


@pytest.mark.parametrize(
    ("heading", "anchor"),
    [
        (
            "8.2 Clasificación de las pruebas (2026-11-26, `main`)",
            "82-clasificación-de-las-pruebas-2026-11-26-main",
        ),
        (
            "D-8. Actualizar yt-dlp desde el programa",
            "d-8-actualizar-yt-dlp-desde-el-programa",
        ),
    ],
)
def test_anchors_follow_github_rules(heading: str, anchor: str) -> None:
    assert load_script().github_anchor(heading) == anchor
