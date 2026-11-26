# Procedimiento de actualización de yt-dlp (SUP-S01)

- **Requisito:** [SUP-S01](../requirements/supplementary-specification.md#mantenibilidad); decisión: [ADR-0002](../notes/adr-0002-pinned-yt-dlp-version.md)
- **Última aplicación:** 2026.10.26 → 2026.11.23 (2026-11-26, por T42-D3; registro en [t42-results.md](../project-management/t42-results.md))

yt-dlp se usa como librería fijada a una versión. Se actualiza a propósito, cuando un sitio deja de funcionar con la versión fijada o hace falta una corrección, nunca de forma automática.

## 1. Cualificar la versión candidata

1. **Versiones actuales:** `uv run queued-media-downloader diagnose` (línea `yt-dlp`: yt-dlp y yt-dlp-ejs; línea `deno`) y `uv pip freeze`.
2. **Versiones disponibles:** `https://pypi.org/pypi/yt-dlp/json`, `…/yt-dlp-ejs/json` y `…/deno/json`. Solo versiones estables de yt-dlp; nunca las `.devN` (nightly).
3. **Evidencia:** descargar la distribución de código de la candidata (`pip download --no-deps --no-binary :all: yt-dlp==<versión>`) y leer en su `Changelog.md` los cambios desde la versión fijada. Buscar en el código el arreglo concreto del defecto; si no se encuentra, la candidata no está justificada.
4. **Compatibilidad:** comprobar en su `pyproject.toml` la versión que exige de yt-dlp-ejs (yt-dlp rechaza cualquier otra) y la mínima de deno.
5. **Impacto sobre los contratos:** comparar, archivo por archivo, el paquete instalado de la candidata con la versión fijada. Los módulos de los que dependen los contratos del proyecto son:

| Módulo de yt-dlp | Contrato del proyecto que depende de él |
|---|---|
| `YoutubeDL.py` | Parámetros de `build_yt_dlp_parameters`; orden `before_dl` → archivo existente → `fixup` → `post_process` (ADR-0030); `prepare_filename`; `paths.temp` (T44); `download()` y su código de salida; `DownloadCancelled`; texto de formato no disponible (UC-06 A1) |
| `postprocessor/common.py`, `ffmpeg.py`, `movefilesafterdownload.py` | Postprocessors de registro y de propiedad; `FFmpegExtractAudio`; hooks de postprocesado; ruta final `after_move` |
| `downloader/common.py`, `http.py`, `fragment.py` | Progress hooks, `continuedl` y peticiones `Range` (UC-06) |
| `extractor/common.py`, `extractor/generic.py`, `extractor/youtube/` | Expansión perezosa (`process=False`), `playlist_count`, media key, `multi_video` |
| `extractor/youtube/jsc/` | Retos de JavaScript con deno y yt-dlp-ejs |
| `utils/` (`sanitize_filename`, excepciones) | Plantilla de los hijos de playlist (ADR-0028); `failure_classifier` |
| `networking/exceptions.py` | Clasificación de fallos de red |

Si uno de esos módulos cambió, leer el cambio y adaptar el código y las pruebas al contrato real; nunca cambiar solo la constante de versión.

## 2. Aplicar

1. Cambiar la versión en `pyproject.toml` (`yt-dlp[default,deno]==<versión>`).
2. `uv lock --upgrade-package yt-dlp` y comprobar con `git diff uv.lock` qué paquetes cambiaron.
3. `uv sync`.
4. Actualizar `VERIFIED_YT_DLP_VERSION` en `tests/media_extraction/test_yt_dlp_format_error_contract.py` solo después de comprobar el contrato (las pruebas de ese archivo lo verifican contra la librería instalada).
   Las pruebas de contrato con textos de yt-dlp son `test_yt_dlp_format_error_contract.py` (formato que ya no se ofrece) y `test_yt_dlp_download_retry_contract.py` (downloader que agota los reintentos); si una falla, revisar la constante correspondiente de `failure_classifier.py` contra el código nuevo de yt-dlp.

## 3. Verificar

1. `uv run python scripts/run_checks.py` (stop-on-error): todas las pruebas, incluidas las de contrato contra la librería real y las descargas de extremo a extremo con el servidor local.
2. `uv run pytest -m network -o addopts=` si el entorno llega a internet; si no (por ejemplo, un proxy que lo bloquea), se clasifican como `BLOCKED_BY_ENVIRONMENT` y se ejecutan en la validación en Windows.
3. Validación en Windows ([guion](../project-management/windows-validation-campaign.md)): al menos el paso 3 y los escenarios afectados por el cambio.

## 4. Documentar

ADR-0002 (seguimiento), SUP-C02, el registro de la validación y la lista de riesgos (R-07).
