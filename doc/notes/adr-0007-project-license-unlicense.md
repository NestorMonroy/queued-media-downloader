# ADR-0007: Licencia del proyecto — The Unlicense

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Nota:** la distribución del material de `doc/reference/` se confirma en [ADR-0025](adr-0025-reference-material-distribution.md).

## Contexto

yt-dlp se publica bajo The Unlicense (el repositorio y PyPI; sus ejecutables empaquetados son GPLv3+). El proyecto incluye binarios de ffmpeg bajo LGPL ([ADR-0005](adr-0005-vendored-ffmpeg-lgpl-shared.md)), que no pueden relicenciarse.

> Nota: este análisis es técnico, no asesoría legal.

## Decisión

El código del proyecto se publica bajo **The Unlicense**. El contenido de `vendor/ffmpeg/` es una **excepción**: conserva su licencia LGPL.

## Consecuencias

- El repositorio no es 100% Unlicense; la excepción debe estar documentada en el `README` y en el archivo de licencia del repositorio.
- Cada build en `vendor/ffmpeg/` incluye su `LICENSE.txt` y un `SOURCE.md` con el origen y la ubicación de su código fuente.
- El proyecto invoca ffmpeg como programa externo (sin enlazarlo), lo que mantiene separado el código propio.
- Cualquier otra dependencia que se distribuya dentro del repositorio requiere revisar su licencia antes de incluirla.
