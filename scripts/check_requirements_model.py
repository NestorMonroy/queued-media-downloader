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
