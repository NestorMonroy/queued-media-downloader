# ADR-0020: Repositorio en GitHub, ramas y Git LFS

- **Estado:** Aceptada
- **Fecha:** 2026-11-23

## Contexto

El proyecto aún no es un repositorio git. Incluye unos 151 MiB de binarios de ffmpeg ([ADR-0018](adr-0018-ffmpeg-build-selection.md)) que, por [ADR-0005](adr-0005-vendored-ffmpeg-lgpl-shared.md), se guardan con Git LFS.

Cuota de Git LFS en GitHub Free (noviembre de 2026): 10 GiB de almacenamiento y 10 GiB de ancho de banda de descarga al mes. Las descargas cuentan contra la cuota del dueño del repositorio, incluidas las de procesos automáticos. Si se agota con presupuesto cero, las descargas de LFS se bloquean hasta el mes siguiente.

## Decisión

- **Alojamiento:** GitHub. Solo el repositorio: sin GitHub Actions ni otros servicios de la plataforma como parte del proceso ([ADR-0021](adr-0021-tdd-and-windows-validation-without-ci.md)).
- **Ramas (*trunk-based*):** `main` siempre funcional; ramas cortas por cambio; integración mediante *pull request*.
- **Antes de integrar** en `main`, quien hace el cambio ejecuta las comprobaciones locales: `ruff format --check`, `ruff check`, `mypy`, `lint-imports` y `pytest` ([ADR-0019](adr-0019-code-quality-tools.md)).
- **Git LFS** se configura antes del primer commit que incluya `vendor/ffmpeg/`, con `.gitattributes` limitado a esa carpeta.

## Consecuencias

- **Riesgo registrado:** cada clon descarga unos 151 MiB de LFS; la cuota gratuita alcanza para unos 68 clones al mes. Si el proyecto tiene más usuarios, habrá que pagar ancho de banda o revisar ADR-0005 (por ejemplo, ffmpeg como asset de una release).
- Sin CI, ningún proceso automático consume la cuota de LFS.
- **Pendiente:** visibilidad del repositorio (público o privado). No bloquea el desarrollo; afecta a la exposición de la cuota de LFS.
