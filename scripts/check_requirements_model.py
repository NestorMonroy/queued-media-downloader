"""Verifica la coherencia del modelo de requisitos y genera su matriz de completitud.

Comprobaciones (todas con stop-on-error en el código de salida):

1. Enlaces: cada enlace relativo de Markdown en doc/ y README.md apunta a un
   archivo existente y, si lleva ancla, a un encabezado de ese archivo (con
   las reglas de anclas de GitHub). El material de terceros de doc/reference/
   se informa aparte y no hace fallar la verificación: no se modifica.
2. Identificadores: cada UC-NN, BR-NN, SUP-XNN, D-NN y R-NN citado en doc/
   existe en su artefacto canónico (una especificación o el modelo para los
   casos de uso retirados, el catálogo de reglas, la especificación
   complementaria, el análisis (encabezado «### D-N.» o fila «| D-N» de su tabla de
   resolución) y la lista de riesgos). Las decisiones son D-N
   sin cero inicial: D-0N identifica los hallazgos de la auditoría previa a la
   aceptación, que no son decisiones.
3. Matriz de completitud: la tabla entre los marcadores
   <!-- completeness-matrix:start --> y <!-- completeness-matrix:end --> de
   doc/requirements/use-case-model.md coincide con la que se calcula a partir
   de las especificaciones. Con --write, la reescribe.
4. Diseño y plataformas: en doc/design/03-target-architecture-and-evolution.md,
   las tablas entre <!-- uc-realization:start --> y <!-- uc-realization:end -->
   y entre <!-- platform-applicability:start --> y
   <!-- platform-applicability:end --> tienen una fila por cada caso de uso
   aceptado, y solo esas, con estados de su vocabulario (DESIGN_STATES y
   PLATFORM_STATES). «Disponible» en Windows CLI exige que el caso de uso tenga
   pruebas automáticas (campo Verificación).
5. Plan de E3 (doc/project-management/iteration-plan-e3.md): la tabla entre
   <!-- e3-coverage:start --> y <!-- e3-coverage:end --> asigna una sola unidad
   a cada flujo no implementado de cada caso de uso aceptado, y «Básico» a los
   casos cuyo campo Estado dice «Implementación: ausente» o «parcial»; no
   asigna flujos implementados ni inexistentes. La tabla entre
   <!-- e3-dependencies:start --> y <!-- e3-dependencies:end --> define las
   unidades y sus dependencias, sin ciclos ni unidades desconocidas, y cada
   unidad cubre algún flujo. Cada regla de «Reglas aprobadas sin implementar» y
   cada requisito suplementario pendiente (sin implementar, parcial, pendiente
   de medición, divergente o condicionado) aparece en el plan. Es consistencia
   documental, no evidencia de implementación.

Estado de un flujo (alternativo o de excepción): la marca explícita
`[estado: IMPLEMENTACIÓN]` o `[estado: IMPLEMENTACIÓN; condicionado]` justo después
de su título en negrita. IMPLEMENTACIÓN es implementado, parcial, defecto,
divergente, ausente o sin cualificar; «condicionado» indica que el flujo tiene una
condición técnica pendiente. Un flujo sin marca, o con un valor desconocido, es un
error: el estado nunca se deduce del texto libre.

Definición de un caso de uso: la primera palabra de su campo Estado (aceptado,
retirado...). Verificación: «prueba en desarrollo» si su campo Verificación
menciona pruebas automáticas; si no, «sin evidencia».

Uso, desde la raíz del repositorio:

    uv run python scripts/check_requirements_model.py            # verificar
    uv run python scripts/check_requirements_model.py --write    # regenerar la matriz
    uv run python scripts/check_requirements_model.py --root RUTA

Termina con 0 si todo es coherente y con 1 si no.
"""

import argparse
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

THIRD_PARTY_DIRECTORY = Path("doc/reference")
USE_CASE_DIRECTORY = Path("doc/requirements/use-cases")
USE_CASE_MODEL = Path("doc/requirements/use-case-model.md")
BUSINESS_RULES = Path("doc/requirements/business-rules.md")
SUPPLEMENTARY = Path("doc/requirements/supplementary-specification.md")
ANALYSIS = Path("doc/requirements/requirements-analysis.md")
RISK_LIST = Path("doc/project-management/risk-list.md")
MATRIX_START = "<!-- completeness-matrix:start -->"
MATRIX_END = "<!-- completeness-matrix:end -->"
DESIGN = Path("doc/design/03-target-architecture-and-evolution.md")
REALIZATION_TABLE = "uc-realization"
APPLICABILITY_TABLE = "platform-applicability"
DESIGN_STATES = ("Realizado", "Definido", "Condicionado")
PLATFORM_STATES = (
    "Disponible",
    "Parcial",
    "Futura",
    "Restringida",
    "No demostrada",
    "No aplicable",
)
PLATFORMS = ("Windows CLI", "Windows GUI", "Android", "iOS")
PLAN = Path("doc/project-management/iteration-plan-e3.md")
COVERAGE_TABLE = "e3-coverage"
DEPENDENCY_TABLE = "e3-dependencies"
BASIC_FLOW = "Básico"
PENDING_SUPPLEMENTARY = re.compile(
    r"sin implementar|parcial|pendiente de medición|divergente|condicionado",
    re.IGNORECASE,
)

FLOW_STATES = (
    "implementado",
    "parcial",
    "defecto",
    "divergente",
    "ausente",
    "sin cualificar",
)
FLOW_STATE = re.compile(r"^\s*`\[estado: ([a-z ]+?)(; condicionado)?\]`")
LINK = re.compile(r"\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6} (.+)$", re.MULTILINE)
CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
FLOW = re.compile(r"^- \*\*([AE]\d+)\.[^\n]*?\*\*(.*)$", re.MULTILINE)
REFERENCES = {
    "UC": re.compile(r"\bUC-(\d{2})\b"),
    "BR": re.compile(r"(?<![A-Z])BR-(\d{2})\b"),
    "SUP": re.compile(r"\bSUP-([A-Z]+\d{2})\b"),
    "D": re.compile(r"(?<![\w-])D-([1-9]\d?)\b"),
    "R": re.compile(r"(?<![A-Z\w-])R-(\d{2})\b"),
}


@dataclass
class UseCaseCounts:
    """Conteos de un caso de uso para la matriz de completitud."""

    identifier: str
    definition: str
    alternatives: int = 0
    exceptions: int = 0
    states: Counter[str] = field(default_factory=Counter)
    conditioned: int = 0
    verification: str = "sin evidencia"
    problems: list[str] = field(default_factory=list)
    pending_flows: list[str] = field(default_factory=list)
    basic_pending: bool = False
    rules: int = 0
    supplementary: int = 0
    criteria: int = 0
    needs_windows: bool = False


def github_anchor(heading: str) -> str:
    """Ancla que GitHub genera para un encabezado."""
    text = re.sub(r"[`*_]|\[([^\]]*)\]\([^)]*\)", r"\1", heading.strip()).lower()
    kept = "".join(
        character
        for character in text
        if character in " -" or unicodedata.category(character)[0] in "LN"
    )
    return kept.replace(" ", "-")


def anchors_of(text: str) -> set[str]:
    """Anclas de los encabezados, con sufijos para los repetidos."""
    seen: Counter[str] = Counter()
    anchors: set[str] = set()
    for heading in HEADING.findall(CODE_BLOCK.sub("", text)):
        anchor = github_anchor(heading)
        anchors.add(anchor if not seen[anchor] else f"{anchor}-{seen[anchor]}")
        seen[anchor] += 1
    return anchors


def link_problems(root: Path) -> tuple[list[str], list[str]]:
    """Enlaces rotos propios y del material de terceros."""
    documents = [*sorted((root / "doc").rglob("*.md")), root / "README.md"]
    anchors = {
        path.resolve(): anchors_of(path.read_text("utf-8")) for path in documents
    }
    own: list[str] = []
    third_party: list[str] = []
    for path in documents:
        text = CODE_BLOCK.sub("", path.read_text("utf-8"))
        for target in LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            target_path, _, fragment = target.partition("#")
            destination = (
                (path.parent / target_path).resolve() if target_path else path.resolve()
            )
            problem = None
            if not destination.exists():
                problem = f"{path.relative_to(root)}: missing {target}"
            elif (
                fragment
                and destination.suffix == ".md"
                and fragment not in anchors.get(destination, set())
            ):
                problem = f"{path.relative_to(root)}: missing anchor {target}"
            if problem:
                relative = path.relative_to(root)
                is_third_party = relative.is_relative_to(THIRD_PARTY_DIRECTORY)
                (third_party if is_third_party else own).append(problem)
    return own, third_party


def defined_identifiers(root: Path) -> dict[str, set[str]]:
    """Identificadores definidos en cada artefacto canónico."""
    model = (root / USE_CASE_MODEL).read_text("utf-8")
    use_cases = {path.name[3:5] for path in (root / USE_CASE_DIRECTORY).glob("uc-*.md")}
    use_cases |= set(re.findall(r"^\| UC-(\d{2}) \|", model, re.MULTILINE))
    rules = (root / BUSINESS_RULES).read_text("utf-8")
    return {
        "UC": use_cases,
        "BR": set(re.findall(r"^\| BR-(\d{2})\b", rules, re.MULTILINE)),
        "SUP": set(
            re.findall(
                r"^\| SUP-([A-Z]+\d{2}) \|",
                (root / SUPPLEMENTARY).read_text("utf-8"),
                re.MULTILINE,
            )
        ),
        "D": set(
            re.findall(
                r"^(?:### |\| )D-(\d{1,2})\b",
                (root / ANALYSIS).read_text("utf-8"),
                re.MULTILINE,
            )
        ),
        "R": set(
            re.findall(
                r"^\| R-(\d{2}) \|", (root / RISK_LIST).read_text("utf-8"), re.MULTILINE
            )
        ),
    }


def identifier_problems(root: Path) -> list[str]:
    """Referencias a identificadores que no están definidos."""
    defined = defined_identifiers(root)
    problems: list[str] = []
    for path in sorted((root / "doc").rglob("*.md")):
        relative = path.relative_to(root)
        if relative.is_relative_to(THIRD_PARTY_DIRECTORY):
            continue
        text = path.read_text("utf-8")
        for kind, pattern in REFERENCES.items():
            for value in sorted(set(pattern.findall(text)) - defined[kind]):
                prefix = "SUP-" if kind == "SUP" else f"{kind}-"
                problems.append(f"{relative}: undefined {prefix}{value}")
    return problems


def section(text: str, title: str) -> str:
    """Contenido de una sección de segundo nivel, sin su encabezado."""
    match = re.search(rf"\n## {re.escape(title)}\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    return match.group(1) if match else ""


def flow_state(text: str) -> tuple[str, bool] | None:
    """Estado de implementación y condición técnica según la marca explícita."""
    match = FLOW_STATE.match(text)
    if match is None or match.group(1) not in FLOW_STATES:
        return None
    return match.group(1), match.group(2) is not None


def use_case_counts(path: Path) -> UseCaseCounts:
    """Conteos de una especificación de caso de uso."""
    text = path.read_text("utf-8")
    identifier = re.search(r"^# (UC-\d{2})", text, re.MULTILINE)
    status = re.search(r"^- \*\*Estado:\*\* ([^;.\n]+)", text, re.MULTILINE)
    if identifier is None or status is None:
        raise ValueError(f"{path}: missing title or Estado field")
    definition = status.group(1).strip().lower().split()[0]
    counts = UseCaseCounts(identifier=identifier.group(1), definition=definition)
    verification = re.search(r"^- \*\*Verificación:\*\* ([^\n]+)", text, re.MULTILINE)
    if verification and "pruebas automáticas" in verification.group(1):
        counts.verification = "prueba en desarrollo"
    flows = FLOW.findall(section(text, "Flujos alternativos")) + FLOW.findall(
        section(text, "Excepciones")
    )
    counts.alternatives = sum(1 for flow, _ in flows if flow.startswith("A"))
    counts.exceptions = sum(1 for flow, _ in flows if flow.startswith("E"))
    for flow, body in flows:
        state = flow_state(body)
        if state is None:
            counts.problems.append(
                f"{path.name}: {flow} has no valid [estado: ...] mark"
            )
            continue
        counts.states[state[0]] += 1
        counts.conditioned += state[1]
        if state[0] != "implementado":
            counts.pending_flows.append(flow)
    status_line = re.search(r"^- \*\*Estado:\*\* ([^\n]+)", text, re.MULTILINE)
    counts.basic_pending = bool(
        status_line
        and re.search(r"Implementación: (ausente|parcial)", status_line.group(1))
    )
    counts.rules = len(set(REFERENCES["BR"].findall(text)))
    counts.supplementary = len(set(REFERENCES["SUP"].findall(text)))
    counts.criteria = len(
        re.findall(r"^\d+\. ", section(text, "Criterios de aceptación"), re.MULTILINE)
    )
    counts.needs_windows = "**Windows**" in text
    return counts


def use_case_rows(root: Path) -> list[UseCaseCounts]:
    """Conteos de todas las especificaciones de casos de uso."""
    return [
        use_case_counts(path)
        for path in sorted((root / USE_CASE_DIRECTORY).glob("uc-*.md"))
    ]


def completeness_matrix(root: Path) -> str:
    """Tabla Markdown de la matriz de completitud."""
    rows = use_case_rows(root)
    header = (
        "| UC | Definición | Alternativos | Excepciones | "
        + " | ".join(state.capitalize() for state in FLOW_STATES)
        + " | Condicionados | Reglas | Suplementarios | Criterios | Verificación"
        + " | Necesita Windows |"
    )
    separator = "|" + "---|" * (10 + len(FLOW_STATES))
    lines = [header, separator]
    for row in rows:
        cells = [
            row.identifier,
            row.definition,
            str(row.alternatives),
            str(row.exceptions),
            *(str(row.states[state]) for state in FLOW_STATES),
            str(row.conditioned),
            str(row.rules),
            str(row.supplementary),
            str(row.criteria),
            row.verification,
            "Sí" if row.needs_windows else "No",
        ]
        lines.append("| " + " | ".join(cells) + " |")
    totals = [
        "**Total**",
        f"**{len(rows)}**",
        f"**{sum(row.alternatives for row in rows)}**",
        f"**{sum(row.exceptions for row in rows)}**",
        *(f"**{sum(row.states[state] for row in rows)}**" for state in FLOW_STATES),
        f"**{sum(row.conditioned for row in rows)}**",
        "—",
        "—",
        f"**{sum(row.criteria for row in rows)}**",
        f"**{sum(row.verification != 'sin evidencia' for row in rows)} con prueba**",
        f"**{sum(row.needs_windows for row in rows)} de {len(rows)}**",
    ]
    lines.append("| " + " | ".join(totals) + " |")
    return "\n".join(lines)


def matrix_problems(root: Path, *, write: bool) -> list[str]:
    """Diferencias entre la matriz publicada y la calculada."""
    model_path = root / USE_CASE_MODEL
    text = model_path.read_text("utf-8")
    if MATRIX_START not in text or MATRIX_END not in text:
        return [f"{USE_CASE_MODEL}: missing completeness-matrix markers"]
    before, rest = text.split(MATRIX_START, 1)
    published, after = rest.split(MATRIX_END, 1)
    expected = completeness_matrix(root)
    if published.strip() == expected:
        return []
    if write:
        model_path.write_text(
            f"{before}{MATRIX_START}\n{expected}\n{MATRIX_END}{after}", "utf-8"
        )
        return []
    return [f"{USE_CASE_MODEL}: completeness matrix is out of date (run with --write)"]


def marked_table_rows(text: str, name: str) -> list[list[str]] | None:
    """Celdas de las filas de casos de uso de una tabla entre marcadores."""
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    if start not in text or end not in text:
        return None
    table = text.split(start, 1)[1].split(end, 1)[0]
    return [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in table.splitlines()
        if line.startswith("| UC-")
    ]


def coverage_problems(
    name: str, rows: list[list[str]], accepted: set[str]
) -> list[str]:
    """Casos de uso aceptados ausentes, repetidos o desconocidos en una tabla."""
    found = Counter(row[0] for row in rows)
    problems = [
        f"{DESIGN}: {name} lacks {identifier}"
        for identifier in sorted(accepted - set(found))
    ]
    problems += [
        f"{DESIGN}: {name} repeats {identifier}"
        for identifier, count in sorted(found.items())
        if count > 1
    ]
    problems += [
        f"{DESIGN}: {name} has {identifier}, which is not an accepted use case"
        for identifier in sorted(set(found) - accepted)
    ]
    return problems


def design_problems(root: Path) -> list[str]:
    """Cobertura y estados de la realización y de la aplicabilidad por plataforma."""
    design_path = root / DESIGN
    if not design_path.exists():
        return [f"{DESIGN}: missing"]
    text = design_path.read_text("utf-8")
    use_cases = {row.identifier: row for row in use_case_rows(root)}
    accepted = {
        identifier
        for identifier, row in use_cases.items()
        if row.definition == "aceptado"
    }
    problems: list[str] = []
    realization = marked_table_rows(text, REALIZATION_TABLE)
    if realization is None:
        problems.append(f"{DESIGN}: missing {REALIZATION_TABLE} markers")
    else:
        problems += coverage_problems(REALIZATION_TABLE, realization, accepted)
        problems += [
            f"{DESIGN}: {row[0]} has unknown design state {row[-1]!r}"
            for row in realization
            if row[-1] not in DESIGN_STATES
        ]
    applicability = marked_table_rows(text, APPLICABILITY_TABLE)
    if applicability is None:
        problems.append(f"{DESIGN}: missing {APPLICABILITY_TABLE} markers")
        return problems
    problems += coverage_problems(APPLICABILITY_TABLE, applicability, accepted)
    for row in applicability:
        for platform, state in zip(
            PLATFORMS, row[1 : 1 + len(PLATFORMS)], strict=False
        ):
            if state not in PLATFORM_STATES:
                problems.append(
                    f"{DESIGN}: {row[0]} has unknown {platform} state {state!r}"
                )
        use_case = use_cases.get(row[0])
        if (
            row[1] == "Disponible"
            and use_case is not None
            and use_case.verification == "sin evidencia"
        ):
            problems.append(
                f"{DESIGN}: {row[0]} is Disponible on Windows CLI"
                " without automated tests"
            )
    return problems


def marked_rows(text: str, name: str) -> list[list[str]] | None:
    """Celdas de las filas de datos de una tabla entre marcadores."""
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    if start not in text or end not in text:
        return None
    table = text.split(start, 1)[1].split(end, 1)[0]
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in table.splitlines()
        if line.startswith("|")
    ]
    return [row for row in rows[2:] if row]


def has_cycle(edges: dict[str, set[str]]) -> bool:
    """Indica si el grafo de dependencias tiene un ciclo."""
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(node: str) -> bool:
        if node in done:
            return False
        if node in visiting:
            return True
        visiting.add(node)
        cyclic = any(visit(target) for target in edges.get(node, set()))
        visiting.discard(node)
        done.add(node)
        return cyclic

    return any(visit(node) for node in edges)


def pending_identifiers(root: Path) -> tuple[set[str], set[str]]:
    """Reglas aprobadas sin implementar y suplementarios pendientes."""
    rules_text = section(
        (root / BUSINESS_RULES).read_text("utf-8"),
        "2. Reglas aprobadas sin implementar",
    )
    rules = set(re.findall(r"^\| (BR-\d{2}) \|", rules_text, re.MULTILINE))
    supplementary = {
        match.group(1)
        for match in re.finditer(
            r"^\| (SUP-[A-Z]+\d{2}) \| ([^|]*)\|",
            (root / SUPPLEMENTARY).read_text("utf-8"),
            re.MULTILINE,
        )
        if PENDING_SUPPLEMENTARY.search(match.group(2))
    }
    return rules, supplementary


def dependency_problems(
    dependencies: list[list[str]],
) -> tuple[dict[str, set[str]], list[str]]:
    """Unidades del plan, dependencias hacia unidades desconocidas y ciclos."""
    edges: dict[str, set[str]] = {}
    for row in dependencies:
        edges.setdefault(row[0], set())
        if row[1] != "—":
            edges[row[0]].update(unit.strip() for unit in row[1].split(","))
    problems = [
        f"{PLAN}: {unit} depends on unknown unit {target}"
        for unit, targets in sorted(edges.items())
        for target in sorted(targets)
        if target not in edges
    ]
    if has_cycle(edges):
        problems.append(f"{PLAN}: the unit dependencies have a cycle")
    return edges, problems


def flow_coverage_problems(
    root: Path, coverage: list[list[str]], units: set[str]
) -> list[str]:
    """Cada flujo pendiente con una sola unidad conocida; cada unidad con flujos."""
    problems: list[str] = []
    assigned: dict[str, Counter[str]] = {}
    for identifier, flows, unit, *_ in coverage:
        if unit not in units:
            problems.append(f"{PLAN}: {identifier} uses unknown unit {unit}")
        assigned.setdefault(identifier, Counter()).update(
            flow.strip() for flow in flows.split(",")
        )
    for use_case in use_case_rows(root):
        if use_case.definition == "aceptado":
            problems += use_case_coverage_problems(
                use_case, assigned.get(use_case.identifier, Counter())
            )
    covered_units = {row[2] for row in coverage}
    problems += [
        f"{PLAN}: {unit} covers no flow" for unit in sorted(units - covered_units)
    ]
    return problems


def use_case_coverage_problems(
    use_case: UseCaseCounts, found: Counter[str]
) -> list[str]:
    """Flujos pendientes sin unidad, repetidos o que no están pendientes."""
    expected = set(use_case.pending_flows)
    if use_case.basic_pending:
        expected.add(BASIC_FLOW)
    identifier = use_case.identifier
    return [
        *(
            f"{PLAN}: {identifier} {flow} has no unit"
            for flow in sorted(expected - set(found))
        ),
        *(
            f"{PLAN}: {identifier} {flow} is assigned twice"
            for flow, count in sorted(found.items())
            if count > 1
        ),
        *(
            f"{PLAN}: {identifier} {flow} is implemented or does not exist"
            for flow in sorted(set(found) - expected)
        ),
    ]


def plan_problems(root: Path) -> list[str]:
    """Cobertura de los flujos, grafo de unidades y requisitos del plan de E3."""
    plan_path = root / PLAN
    if not plan_path.exists():
        return [f"{PLAN}: missing"]
    text = plan_path.read_text("utf-8")
    dependencies = marked_rows(text, DEPENDENCY_TABLE)
    coverage = marked_rows(text, COVERAGE_TABLE)
    if dependencies is None or coverage is None:
        return [f"{PLAN}: missing {DEPENDENCY_TABLE} or {COVERAGE_TABLE} markers"]
    edges, problems = dependency_problems(dependencies)
    problems += flow_coverage_problems(root, coverage, set(edges))
    rules, supplementary = pending_identifiers(root)
    mentioned = set(re.findall(r"\b(?:BR|SUP)-[A-Z]*\d{2}\b", text))
    problems += [
        f"{PLAN}: {identifier} has no strategy in the plan"
        for identifier in sorted((rules | supplementary) - mentioned)
    ]
    return problems


def main() -> int:
    """Ejecuta las verificaciones y devuelve 0 si el modelo es coherente."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true", help="regenerate the matrix")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    own_links, third_party_links = link_problems(root)
    problems = [
        *(problem for row in use_case_rows(root) for problem in row.problems),
        *own_links,
        *identifier_problems(root),
        *matrix_problems(root, write=arguments.write),
        *design_problems(root),
        *plan_problems(root),
    ]
    for problem in problems:
        print(problem)
    print(
        f"links: {len(own_links)} broken; "
        f"third-party (not modified, not failing): {len(third_party_links)}"
    )
    print(
        "requirements model: " + ("OK" if not problems else f"{len(problems)} problems")
    )
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
