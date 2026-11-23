# ADR-0018: Build de ffmpeg incluida en el repositorio

- **Estado:** Aceptada
- **Fecha:** 2026-11-23
- **Resuelve:** el pendiente de [ADR-0005](adr-0005-vendored-ffmpeg-lgpl-shared.md) (versión concreta y límite por archivo)

## Contexto

ADR-0005 decidió incluir ffmpeg y ffprobe en `vendor/ffmpeg/`, en variante LGPL compartida, sin `ffplay.exe`, con Git LFS. Faltaba elegir fuente, versión y build.

Fuentes evaluadas:
- **yt-dlp/FFmpeg-Builds:** su última release es del 22 de agosto de 2026, y su propio README indica que sus builds ya son equivalentes a las de FFmpeg sin parches.
- **BtbN/FFmpeg-Builds:** el proyecto del que deriva el anterior. Publica builds de `master` y de la rama 9.0, en variantes GPL y LGPL, estáticas y compartidas.

Medición de `ffmpeg-n9.0-latest-win64-lgpl-shared-9.0.zip` (BtbN, descargada el 2026-11-23):

| Contenido | Tamaño |
|---|---|
| `bin/` sin `ffplay.exe` | 150,7 MiB |
| Archivo más grande: `avcodec-63.dll` | 89,7 MiB (límite de GitHub: 100 MiB) |
| `ffmpeg.exe` / `ffprobe.exe` | 0,5 MiB / 0,3 MiB |
| Licencia | `LICENSE.txt` incluido |

## Decisión

- **Fuente:** BtbN/FFmpeg-Builds.
- **Versión:** rama de release **9.0** (más estable que `master` para un binario versionado).
- **Variante:** `win64-lgpl-shared`.
- **Contenido de `vendor/ffmpeg/<version>-win64-lgpl-shared/`:** `bin/` sin `ffplay.exe`, `LICENSE.txt` y `SOURCE.md`. No se incluyen `doc/`, `include/` ni `lib/`.
- **Fijación:** se usa una build con fecha (no `latest`), preferiblemente la última de un mes. `SOURCE.md` registra la URL exacta, la fecha, el SHA-256 del zip y el enlace al código fuente de esa versión (obligación de la LGPL, [ADR-0007](adr-0007-project-license-unlicense.md)).

## Consecuencias

- El repositorio crece unos 151 MiB por cada versión de ffmpeg incluida (almacenados en Git LFS, [ADR-0020](adr-0020-repository-branching-and-lfs.md)).
- `avcodec-63.dll` queda a 10 MiB del límite por archivo; una versión futura podría superarlo. Git LFS lo evita, pero hay que comprobarlo en cada actualización.
- Pendiente de verificar al incluir la build: la política de conservación de builds con fecha de BtbN (en sus forks, la última build de cada mes se conserva dos años).
