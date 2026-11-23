# ADR-0019: Herramientas de calidad de código e idioma de los comentarios

- **Estado:** Aceptada
- **Fecha:** 2026-11-23
- **Resuelve:** los pendientes de [ADR-0011](adr-0011-code-conventions.md) (herramientas e idioma de los comentarios)

## Contexto

ADR-0011 dejó pendientes el formateador, el linter, el verificador de tipos y el idioma de los comentarios en línea. El linter de importaciones ya se decidió en [ADR-0017](adr-0017-ffmpeg-inspired-public-api-and-dependency-graph.md).

Situación de los verificadores de tipos (noviembre de 2026):
- **ty** (Astral): en beta, con versiones 0.0.x y sin API estable; puede haber cambios incompatibles entre versiones.
- **mypy** y **pyright**: estables y maduros.

## Decisión

| Necesidad | Herramienta | Comando |
|---|---|---|
| Formato | Ruff (`ruff format`) | `uv run ruff format` |
| Linter | Ruff (`ruff check`) | `uv run ruff check` |
| Tipos | mypy | `uv run mypy` |
| Importaciones | import-linter (ADR-0017) | `uv run lint-imports` |
| Pruebas | pytest ([ADR-0021](adr-0021-tdd-and-windows-validation-without-ci.md)) | `uv run pytest` |

- Todas son dependencias del grupo `dev` de `pyproject.toml` y se configuran en ese archivo.
- **Anotaciones de tipo obligatorias** en todo el código del paquete; mypy se ejecuta en modo estricto.
- **ty se reevaluará** cuando publique una versión estable.
- **Comentarios en línea en español,** como los docstrings: explican el código a personas. La regla de idioma queda así: lo que lee el programa o el usuario final (identificadores, mensajes, logs) en inglés; lo que explica el código (docstrings y comentarios) en español. Siguiendo las [guías](../reference/clean-code-guidelines/practise/comment.md), los comentarios se usan poco: explican el porqué, no repiten el qué.

## Consecuencias

- Ruff sustituye a varias herramientas (formateador, ordenador de imports, linters) y es del mismo autor que uv.
- La configuración concreta de reglas de Ruff y mypy se define en la iteración E1.
- Con esta decisión, ADR-0011 no tiene pendientes.
