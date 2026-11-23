# ADR-0003: Empaquetado con uv y `pyproject.toml`

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto

El usuario final instala el proyecto en Windows con el mínimo de pasos. yt-dlp requiere Python ≥3.11. Se evaluaron `requirements.txt` con pip y `pyproject.toml` con uv.

Hallazgos en PyPI (yt-dlp 2026.10.26):
- `pip install yt-dlp` sin extras no instala ninguna dependencia.
- El extra `default` incluye brotli, certifi, mutagen, pycryptodomex, requests, urllib3, websockets y yt-dlp-ejs.
- El extra `deno` instala el runtime de JavaScript como paquete pip (wheel `win_amd64`, 42 MB).
- Los extras `pin`/`pin-*` fijan las mismas dependencias a versiones exactas.

## Opciones consideradas

1. **`requirements.txt` + pip:** universal, pero requiere Python preinstalado y no fija dependencias transitivas salvo a mano.
2. **`pyproject.toml` + uv + `uv.lock`:** uv puede instalar el Python necesario y el lock fija todo el árbol con hashes.

## Decisión

- **`pyproject.toml` es la única fuente de verdad** y **uv** la herramienta principal, con `uv.lock` versionado.
- Dependencia: `yt-dlp[default,deno]==2026.10.26`. Los extras `pin` no son necesarios: el lock ya fija el árbol completo.
- El punto de entrada se declara en `[project.scripts]`.
- `[tool.uv] environments` restringe la resolución a las plataformas soportadas ([ADR-0004](adr-0004-windows-x64-target-platform.md)).
- Para quien use pip, `requirements.txt` se **genera** con `uv export --format requirements-txt`; no se mantiene a mano.

## Consecuencias

- El usuario no necesita Python instalado: `uv sync` lo descarga si falta.
- Flujo de uso: `git clone` → `uv sync` → `uv run <comando>`.
- deno queda dentro del entorno virtual, sin instalación en el sistema.
- ffmpeg no se puede instalar por esta vía (ver [ADR-0005](adr-0005-vendored-ffmpeg-lgpl-shared.md)).
- La caché de uv (`%LOCALAPPDATA%\uv\cache`) ocupa disco; documentar `uv cache prune` para equipos modestos.
