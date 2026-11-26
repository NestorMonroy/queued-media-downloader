"""Inventario estructural y grafo de componentes de queued_media_downloader.

Experimento de Analysis and Design (instrucción 2.3.0, §14 a §18). No es código
de producción ni lo ejecuta pytest. Solo lee el código fuente: no importa el
paquete, no abre la base de datos y no escribe fuera de --output.

Cuenta por componente los módulos, las clases por tipo (dataclass, Protocol,
Enum, excepción), las funciones y los métodos, la API pública (__all__), las
dependencias entre componentes, las de terceros y los módulos de la biblioteca
estándar que ligan a un mecanismo variable (procesos, SQLite, consola, sistema
operativo). Obtiene el grafo con grimp, la misma librería que usa lint-imports.
"""

import argparse
import ast
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import grimp

PACKAGE = "queued_media_downloader"
# Módulos de la biblioteca estándar que ligan a un mecanismo que varía entre
# interfaces o plataformas (§18). Usarlos no es un defecto: el inventario dice
# dónde están para comprobar que no están en una responsabilidad estable.
VARIABLE_MECHANISMS = {
    "argparse": "interfaz de línea de comandos",
    "ctypes": "API nativa del sistema operativo",
    "multiprocessing": "procesos",
    "signal": "señales del sistema operativo",
    "sqlite3": "SQLite",
    "subprocess": "procesos externos",
    "tomllib": "formato del archivo de configuración",
    "msvcrt": "consola de Windows",
}
STANDARD_LIBRARY = set(sys.stdlib_module_names)


def _top_name(module: str) -> str:
    return module.split(".")[0]


def _class_kind(node: ast.ClassDef) -> str:
    bases = {ast.unparse(base).split(".")[-1].split("[")[0] for base in node.bases}
    decorators = {ast.unparse(item).split("(")[0] for item in node.decorator_list}
    if "Protocol" in bases:
        return "protocol"
    if bases & {"Enum", "StrEnum", "IntEnum"}:
        return "enum"
    if any(base.endswith(("Error", "Exception")) for base in bases):
        return "exception"
    if decorators & {"dataclass", "dataclasses.dataclass"}:
        return "dataclass"
    if "NamedTuple" in bases:
        return "named_tuple"
    return "class"


def _public_names(tree: ast.Module) -> list[str]:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            return [ast.literal_eval(item) for item in node.value.elts]  # type: ignore[attr-defined]
    return []


def _imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def inspect_module(path: Path) -> dict[str, Any]:
    """Cuenta los elementos de un módulo y sus imports."""
    tree = ast.parse(path.read_text("utf-8"))
    classes: Counter[str] = Counter()
    methods = 0
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes[_class_kind(node)] += 1
            methods += sum(
                isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
                for item in node.body
            )
    functions = sum(
        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) for node in tree.body
    )
    imports = _imported_modules(tree)
    return {
        "lines": len(path.read_text("utf-8").splitlines()),
        "classes": dict(classes),
        "functions": functions,
        "methods": methods,
        "public_names": _public_names(tree),
        "imports": sorted(imports),
    }


def inventory_components(package_root: Path) -> dict[str, Any]:
    """Agrega el inventario por componente (subpaquete de primer nivel)."""
    components: dict[str, Any] = {}
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root)
        component = relative.parts[0] if len(relative.parts) > 1 else "(root)"
        module = inspect_module(path)
        entry = components.setdefault(
            component,
            {
                "modules": [],
                "lines": 0,
                "classes": Counter(),
                "functions": 0,
                "methods": 0,
                "public_api": [],
                "third_party": set(),
                "variable_mechanisms": {},
            },
        )
        entry["modules"].append(str(relative))
        entry["lines"] += module["lines"]
        entry["classes"].update(module["classes"])
        entry["functions"] += module["functions"]
        entry["methods"] += module["methods"]
        if path.name == "__init__.py" and len(relative.parts) == 2:
            entry["public_api"] = module["public_names"]
        for imported in module["imports"]:
            top = _top_name(imported)
            if top in VARIABLE_MECHANISMS:
                entry["variable_mechanisms"].setdefault(top, []).append(str(relative))
            elif top not in STANDARD_LIBRARY and top != PACKAGE:
                entry["third_party"].add(top)
    for entry in components.values():
        entry["classes"] = dict(entry["classes"])
        entry["third_party"] = sorted(entry["third_party"])
        entry["module_count"] = len(entry["modules"])
    return components


def component_graph() -> dict[str, Any]:
    """Grafo de imports directos entre componentes, con detección de ciclos."""
    graph = grimp.build_graph(PACKAGE)
    names = sorted(
        module.split(".")[1]
        for module in graph.find_children(PACKAGE)
        if graph.find_children(module)
    )
    edges: dict[str, list[str]] = {}
    for source in names:
        targets = []
        for target in names:
            if source != target and graph.direct_import_exists(
                importer=f"{PACKAGE}.{source}",
                imported=f"{PACKAGE}.{target}",
                as_packages=True,
            ):
                targets.append(target)
        edges[source] = targets
    cycles = [
        (source, target)
        for source, targets in edges.items()
        for target in targets
        if source in edges.get(target, [])
    ]
    return {"components": names, "edges": edges, "mutual_imports": cycles}


def inventory_tests(tests_root: Path) -> dict[str, Any]:
    """Pruebas por carpeta y cuántas llevan la marca windows."""
    per_directory: Counter[str] = Counter()
    windows = 0
    for path in tests_root.rglob("test_*.py"):
        source = path.read_text("utf-8")
        tree = ast.parse(source)
        count = sum(
            isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            for node in ast.walk(tree)
        )
        relative = path.relative_to(tests_root)
        per_directory[relative.parts[0] if len(relative.parts) > 1 else "."] += count
        windows += source.count("pytest.mark.windows")
    return {
        "test_functions_by_directory": dict(sorted(per_directory.items())),
        "test_functions": sum(per_directory.values()),
        "windows_marks": windows,
    }


def main() -> int:
    """Escribe el inventario en JSON."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    repository = Path(__file__).resolve().parents[2]
    result = {
        "python": sys.version.split()[0],
        "components": inventory_components(repository / PACKAGE),
        "graph": component_graph(),
        "tests": inventory_tests(repository / "tests"),
    }
    arguments.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=sorted) + "\n",
        "utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
