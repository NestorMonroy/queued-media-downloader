import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "check_requirements_model.py"

USE_CASE = """# UC-01: Encolar

- **Estado:** aceptado (Responsable). Implementación: parcial.
- **Verificación:** pruebas automáticas en desarrollo.

## Flujos alternativos

- **A1. Uno vigente:** `[estado: implementado]` con los valores por defecto.
- **A2. Otro sin implementar** `[estado: ausente; condicionado]`:
  según [BR-01](../business-rules.md).

## Excepciones

- **E1. Uno defectuoso:** `[estado: defecto]` **Defecto (R-01):** falla mal.

## Criterios de aceptación

1. Funciona.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Uno | **Windows** |
"""

DESIGN = """# Diseño

<!-- uc-realization:start -->
| UC | Responsabilidades | Diseño |
|---|---|---|
| UC-01 | Encolar | Definido |
<!-- uc-realization:end -->

<!-- platform-applicability:start -->
| UC | Windows CLI | Windows GUI | Android | iOS | Condición |
|---|---|---|---|---|---|
| UC-01 | Disponible | Futura | Restringida | No demostrada | — |
<!-- platform-applicability:end -->
"""

PLAN = """# Plan

<!-- e3-dependencies:start -->
| Unidad | Depende de | Tipo | Motivo |
|---|---|---|---|
| U1 | — | — | Primera |
| U2 | U1 | Implementación | Segunda |
<!-- e3-dependencies:end -->

<!-- e3-coverage:start -->
| UC | Flujos | Unidad | Planificación | Horizonte o condición |
|---|---|---|---|---|
| UC-01 | Básico, A2 | U1 | Planificado | E3 |
| UC-01 | E1 | U2 | Planificado | E3 |
<!-- e3-coverage:end -->
"""
ROADMAP_PATH = "doc/product-management/product-roadmap.md"
ROADMAP = """# Hoja de ruta

| Horizonte | Contenido |
|---|---|
| H1. Primera | Algo |
| H5. Posterior | Otra cosa |
"""


PLAN_PATH = "doc/project-management/iteration-plan-e3.md"
GOVERNANCE_PATH = "doc/project-management/governance.md"
GOVERNANCE = """# Gobierno

<!-- decision-register:start -->
| D | Decisión | Responsabilidad | Estado |
|---|---|---|---|
| D-1 | Algo | Requisitos | Aprobada |
<!-- decision-register:end -->
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
    write(tmp_path / "doc/design/03-target-architecture-and-evolution.md", DESIGN)
    write(tmp_path / "doc/project-management/iteration-plan-e3.md", PLAN)
    write(tmp_path / GOVERNANCE_PATH, GOVERNANCE)
    write(tmp_path / ROADMAP_PATH, ROADMAP)
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
        "| UC-01 | aceptado | 2 | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 1 "
        "| prueba en desarrollo | Sí |" in model
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
            "## Excepciones", "- **A3. Nuevo** `[estado: ausente]`.\n\n## Excepciones"
        ),
        encoding="utf-8",
    )

    write(repository / PLAN_PATH, PLAN.replace("| E1 | U2 |", "| E1, A3 | U2 |"))
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
        (
            " `[estado: implementado]` con los valores por defecto",
            ("implementado", False, False),
        ),
        (" `[estado: defecto]` **Defecto (R-28):** falla", ("defecto", False, False)),
        (" `[estado: ausente; condicionado]` (D-1)", ("ausente", True, False)),
        (" `[estado: sin cualificar]`", ("sin cualificar", False, False)),
        (" `[estado: ausente; propuesto]`", ("ausente", False, True)),
        (" `[estado: ausente; condicionado; propuesto]`", ("ausente", True, True)),
    ],
)
def test_flow_state_comes_only_from_the_explicit_mark(
    text: str, state: tuple[str, bool, bool]
) -> None:
    assert load_script().flow_state(text) == state


@pytest.mark.parametrize(
    "text",
    [" (propuesto) sin marca", " **Defecto (R-28):** sin marca", " `[estado: quizá]`"],
)
def test_text_without_a_valid_mark_is_not_classified(text: str) -> None:
    assert load_script().flow_state(text) is None


def test_a_flow_without_a_mark_fails(repository: Path) -> None:
    use_case = repository / "doc/requirements/use-cases/uc-01-enqueue.md"
    use_case.write_text(
        USE_CASE.replace(
            "## Excepciones", "- **A3. Sin marca** (propuesto).\n\n## Excepciones"
        ),
        encoding="utf-8",
    )

    result = check(repository)

    assert result.returncode == 1
    assert "A3 has no valid [estado: ...] mark" in result.stdout


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


DESIGN_PATH = "doc/design/03-target-architecture-and-evolution.md"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            ("| UC-01 | Encolar | Definido |\n", ""),
            "uc-realization lacks UC-01",
        ),
        (
            ("| UC-01 | Encolar | Definido |", "| UC-01 | Encolar | Casi |"),
            "UC-01 has unknown design state 'Casi'",
        ),
        (
            ("| Restringida |", "| Quizá |"),
            "UC-01 has unknown Android state 'Quizá'",
        ),
        (
            ("| UC-01 | Disponible |", "| UC-01 | Disponible |\n| UC-01 | Futura |"),
            "platform-applicability repeats UC-01",
        ),
        (
            (
                "<!-- uc-realization:end -->",
                "| UC-44 | Otro | Definido |\n<!-- uc-realization:end -->",
            ),
            "uc-realization has UC-44, which is not an accepted or candidate use case",
        ),
        (
            ("<!-- platform-applicability:start -->", ""),
            "missing platform-applicability markers",
        ),
    ],
)
def test_the_design_tables_cover_each_accepted_use_case_with_known_states(
    repository: Path, change: tuple[str, str], message: str
) -> None:
    write(repository / DESIGN_PATH, DESIGN.replace(*change))

    result = check(repository)

    assert result.returncode == 1
    assert message in result.stdout


def test_available_on_windows_requires_automated_tests(repository: Path) -> None:
    use_case = repository / "doc/requirements/use-cases/uc-01-enqueue.md"
    use_case.write_text(
        USE_CASE.replace("pruebas automáticas en desarrollo", "ninguna todavía"),
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(repository), "--write"],
        check=False,
        capture_output=True,
        timeout=60,
    )

    result = check(repository)

    assert result.returncode == 1
    assert "UC-01 is Disponible on Windows CLI without automated tests" in result.stdout


@pytest.mark.parametrize(
    ("change", "messages"),
    [
        (
            ("| UC-01 | E1 | U2 | Planificado | E3 |\n", ""),
            ["UC-01 E1 has no unit", "U2 has no Planificado flow"],
        ),
        (
            ("| UC-01 | E1 | U2 |", "| UC-01 | E1, A2 | U2 |"),
            ["UC-01 A2 is assigned twice"],
        ),
        (
            ("| UC-01 | E1 | U2 |", "| UC-01 | E1, A1 | U2 |"),
            ["UC-01 A1 is implemented or does not exist"],
        ),
        (
            ("| UC-01 | E1 | U2 |", "| UC-01 | E1 | U9 |"),
            ["UC-01 is Planificado with unknown unit U9", "U2 has no Planificado flow"],
        ),
        (
            ("| U1 | — | — | Primera |", "| U1 | U2 | Diseño | Primera |"),
            ["the unit dependencies have a cycle"],
        ),
        (
            ("| U2 | U1 |", "| U2 | U7 |"),
            ["U2 depends on unknown unit U7"],
        ),
    ],
)
def test_the_e3_plan_covers_each_pending_flow_once_with_acyclic_units(
    repository: Path, change: tuple[str, str], messages: list[str]
) -> None:
    write(repository / PLAN_PATH, PLAN.replace(*change))

    result = check(repository)

    assert result.returncode == 1
    for message in messages:
        assert message in result.stdout


def test_a_pending_rule_or_requirement_needs_a_strategy_in_the_plan(
    repository: Path,
) -> None:
    write(
        repository / "doc/requirements/business-rules.md",
        "# Reglas\n\n## 2. Reglas aprobadas sin implementar\n\n| BR-01 | C | Regla |\n",
    )
    write(
        repository / "doc/requirements/supplementary-specification.md",
        "# Suplementarios\n\n| SUP-F01 | **Aceptado, sin implementar:** salida |\n",
    )

    result = check(repository)

    assert result.returncode == 1
    assert "BR-01 has no strategy in the plan" in result.stdout
    assert "SUP-F01 has no strategy in the plan" in result.stdout
    write(repository / PLAN_PATH, PLAN + "\nBR-01 y SUP-F01 en U1.\n")
    assert check(repository).returncode == 0


PROPOSED_FLOW = "- **A3. Propuesto** `[estado: ausente; propuesto]`: amplía.\n\n"
CANDIDATE = """# UC-02: Candidato

- **Estado:** candidato (pendiente de aprobación). Implementación: ausente.
- **Verificación:** sin evidencia.

## Flujos alternativos

- **A1. Una alternativa** `[estado: ausente]`: algo.
"""


def add_proposed_flow(repository: Path) -> None:
    use_case = repository / "doc/requirements/use-cases/uc-01-enqueue.md"
    use_case.write_text(
        USE_CASE.replace("## Excepciones", PROPOSED_FLOW + "## Excepciones"),
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(repository), "--write"],
        check=False,
        capture_output=True,
        timeout=60,
    )


def test_a_proposed_flow_is_planned_as_a_candidate(repository: Path) -> None:
    add_proposed_flow(repository)
    assert "UC-01 A3 has no unit" in check(repository).stdout

    write(
        repository / PLAN_PATH,
        PLAN.replace(
            "<!-- e3-coverage:end -->",
            "| UC-01 | A3 | U2 | Planificado | E3 |\n<!-- e3-coverage:end -->",
        ),
    )
    assert "UC-01 A3 awaits approval and must be Candidato" in check(repository).stdout

    write(
        repository / PLAN_PATH,
        PLAN.replace(
            "<!-- e3-coverage:end -->",
            "| UC-01 | A3 | — | Candidato | H5 |\n<!-- e3-coverage:end -->",
        ),
    )
    assert check(repository).returncode == 0


@pytest.mark.parametrize(
    ("row", "message"),
    [
        (
            "| UC-01 | E1 | U2 | Quizá | E3 |",
            "UC-01 has unknown planning state 'Quizá'",
        ),
        (
            "| UC-01 | E1 | U9 | Planificado | E3 |",
            "UC-01 is Planificado with unknown unit U9",
        ),
        ("| UC-01 | E1 | U2 | Futuro | H5 |", "UC-01 is Futuro but names unit U2"),
        (
            "| UC-01 | E1 | — | Futuro | más tarde |",
            "UC-01 is Futuro without a roadmap horizon",
        ),
        (
            "| UC-01 | E1 | — | Futuro | H9 |",
            "UC-01 is Futuro without a roadmap horizon",
        ),
        (
            "| UC-01 | E1 | — | Candidato | H5 |",
            "UC-01 E1 is approved and cannot be Candidato",
        ),
        (
            "| UC-01 | E1 | U2 | Bloqueado | D-1 |",
            "UC-01 is Bloqueado without a pending decision",
        ),
        (
            "| UC-01 | E1 | — | No aplicable | — |",
            "UC-01 is No aplicable without a reason",
        ),
    ],
)
def test_each_planning_state_needs_its_justification(
    repository: Path, row: str, message: str
) -> None:
    write(
        repository / PLAN_PATH,
        PLAN.replace("| UC-01 | E1 | U2 | Planificado | E3 |", row),
    )

    assert message in check(repository).stdout


def test_future_and_blocked_flows_are_valid_with_their_justification(
    repository: Path,
) -> None:
    write(
        repository / GOVERNANCE_PATH,
        GOVERNANCE.replace(
            "<!-- decision-register:end -->",
            "| D-2 | Otra | Requisitos | Pendiente |\n<!-- decision-register:end -->",
        ),
    )
    write(
        repository / "doc/requirements/requirements-analysis.md",
        "# Análisis\n\n### D-1. Algo\n\n### D-2. Otra\n",
    )
    plan = PLAN.replace(
        "| UC-01 | Básico, A2 | U1 | Planificado | E3 |",
        "| UC-01 | Básico | U1 | Planificado | E3 |\n| UC-01 | A2 | — | Futuro | H5 |",
    ).replace(
        "| UC-01 | E1 | U2 | Planificado | E3 |",
        "| UC-01 | E1 | U2 | Bloqueado | Depende de D-2 |",
    )
    write(repository / PLAN_PATH, plan)

    result = check(repository)

    assert "UC-01" not in result.stdout.replace("U2 has no Planificado flow", "")
    assert "U2 has no Planificado flow" in result.stdout


def test_a_candidate_use_case_is_planned_as_a_proposal_and_designed_as_a_candidate(
    repository: Path,
) -> None:
    write(repository / "doc/requirements/use-cases/uc-02-candidate.md", CANDIDATE)
    subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(repository), "--write"],
        check=False,
        capture_output=True,
        timeout=60,
    )
    result = check(repository)
    assert "UC-02 A1 has no unit" in result.stdout
    assert "UC-02 Básico has no unit" in result.stdout
    assert "uc-realization lacks UC-02" in result.stdout

    write(
        repository / PLAN_PATH,
        PLAN.replace(
            "<!-- e3-coverage:end -->",
            "| UC-02 | Básico, A1 | — | Candidato | H5 |\n<!-- e3-coverage:end -->",
        ),
    )
    design = DESIGN.replace(
        "<!-- uc-realization:end -->",
        "| UC-02 | Propuesta | Definido |\n<!-- uc-realization:end -->",
    ).replace(
        "<!-- platform-applicability:end -->",
        "| UC-02 | Futura | Futura | Futura | No demostrada | — |\n"
        "<!-- platform-applicability:end -->",
    )
    write(repository / DESIGN_PATH, design)
    assert (
        "UC-02 must be 'Candidato' only if it is a candidate"
        in check(repository).stdout
    )

    write(
        repository / DESIGN_PATH,
        design.replace(
            "| UC-02 | Propuesta | Definido |", "| UC-02 | Propuesta | Candidato |"
        ),
    )
    assert check(repository).returncode == 0


def test_a_proposal_is_not_mixed_with_approved_requirements(repository: Path) -> None:
    write(
        repository / "doc/requirements/business-rules.md",
        "# Reglas\n\n## 2. Reglas aprobadas sin implementar\n\n| BR-01 | C | Regla |\n"
        "\n## 5. Reglas propuestas\n\n| BR-01 | C | Regla |\n| BR-02 | C | Otra |\n",
    )
    write(
        repository / "doc/requirements/supplementary-specification.md",
        "# Suplementarios\n\n| SUP-F01 | **Aceptado; propuesto:** salida |\n",
    )

    result = check(repository)

    assert "BR-01 is both proposed and approved" in result.stdout
    assert "SUP-F01 is both proposed and accepted" in result.stdout
    assert "BR-02 has no strategy in the plan" in result.stdout


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ("", "D-1 is not registered"),
        (
            "| D-1 | Algo | Requisitos | Aprobada |\n"
            "| D-1 | Algo | Requisitos | Aprobada |",
            "D-1 is registered twice",
        ),
        (
            "| D-1 | Algo | Requisitos | Aprobada |\n"
            "| D-9 | Otra | Requisitos | Aprobada |",
            "D-9 is not a defined decision",
        ),
        ("| D-1 | Algo | Requisitos | Quizá |", "D-1 has unknown state 'Quizá'"),
    ],
)
def test_the_decision_register_lists_each_decision_once_with_a_known_state(
    repository: Path, row: str, message: str
) -> None:
    write(
        repository / GOVERNANCE_PATH,
        GOVERNANCE.replace("| D-1 | Algo | Requisitos | Aprobada |", row),
    )

    result = check(repository)

    assert result.returncode == 1
    assert message in result.stdout


def test_a_missing_decision_register_fails(repository: Path) -> None:
    (repository / GOVERNANCE_PATH).unlink()

    assert "governance.md: missing" in check(repository).stdout
