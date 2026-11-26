# Registro de resultados de la campaña T42

- **Guion:** [windows-validation-campaign.md](windows-validation-campaign.md)
- **Evaluador en Windows:** Responsable del proyecto
- **Equipo:** Windows 11 Home Single Language 10.0.26200 (build 26200), AMD64; PowerShell 7.6.9; uv 0.11.8; Python 3.12.13; git 2.53.0; git-lfs 3.7.1
- **Evidencia:** carpeta `C:\qmd-t42\` del Evaluador (entregada como `qmd-t42.7z`); el JSON del experimento se copió a [t33-windows-results-candidate-1.json](../notes/experiments/t33-windows-results-candidate-1.json)

## Candidato `t42-candidate-1` (`5f30151f055c2f9b8b2602a19aa79a9a093531de`, 2026-11-25)

`Test-CampaignCandidate` confirmó la etiqueta en el clon y en GitHub (`evidence\candidate.txt`).

| Paso | Resultado | Evidencia | Observaciones |
|---|---|---|---|
| 1 Instalación | **pasa** | Salida de la consola; `environment.txt` | `git clone` con LFS, `uv sync` sin errores |
| 2 `diagnose` | **no ejecutado** | — | No se ejecutó; queda para el siguiente candidato |
| 3 Suites | **falla** | `step3-run-checks.log`, `step3-pytest-windows.log`, `step3-pytest-network.log`, `exit-codes.txt` | Formato, linter, tipos e importaciones pasan. `pytest`: 527 pasadas, 1 fallida (**T42-D1**), 7 omitidas por diseño, 19 deseleccionadas. `pytest -m windows`: **16 pasadas** (en Windows llevan también la marca `windows` las 6 pruebas del terminador parametrizadas para la plataforma). `pytest -m network`: **3 pasadas**: la clasificación `BLOCKED_BY_ENVIRONMENT` del entorno de desarrollo no se aplica en Windows |
| 4 Experimento T33 | **pasa para D1; incompleto** | `step4-t33-experiment.log`, JSON | Los cuatro escenarios de `job_object`: *ninguno vivo*. Cinco filas `ERROR` de las estrategias de comparación y del control de asignación tardía (**T42-D2**) |
| 5.1 | **pasa (parcial)** | `queue-5.1.log`, cola `queues\5.1` | Solo el primer `enqueue` (video con unión): `COMPLETED`, archivo AV1 + Opus de 19 s y 474 478 bytes (comprobado con `ffprobe`), carpeta `.partial` vacía, reclamación con el owner token del job, esquema 4. Faltan el `--audio-only` y el duplicado. Aviso de yt-dlp: **T42-D3** |
| 5.2 a 13 | **no ejecutados** | — | — |

### Defectos

| Id | Paso | Origen | Gravedad | Descripción | Estado |
|---|---|---|---|---|---|
| T42-D1 | 3 | *Prueba* | Menor (bloquea el paso 3 obligatorio hasta repetirlo) | `test_job_without_progress_is_terminated_with_its_child_after_the_grace_period` abría el handle del hijo **después** de que el árbol se terminara; el PID ya no existía y `OpenProcess` falló con `WinError 87`. Que el PID no existiera es coherente con que el hijo se terminó, pero la prueba no llegó a comprobarlo. En Linux pasaba porque el hijo quedaba como zombi un instante | Corregido en `t42-candidate-2`: el handle se abre antes de pedir la cancelación, con el hijo vivo |
| T42-D2 | 4 | *Herramienta de la campaña* (experimento) | Menor | Al terminar un escenario, la limpieza mataba los procesos que la estrategia deja vivos a propósito y borraba la carpeta temporal sin esperar a que salieran; en Windows `TerminateProcess` es asíncrono y el parcial seguía abierto (`PermissionError 13`). Se perdían esas observaciones, no las de `job_object` | Corregido en `t42-candidate-2`: la limpieza espera a que salgan y una carpeta retenida ya no descarta la observación |
| T42-D3 | 5.1 | *Producto, general* (externo: cambio de YouTube frente a yt-dlp 2026.10.26 y yt-dlp-ejs 0.8.0 fijados) | Mayor | El solucionador de retos `n` de yt-dlp-ejs falla en deno con el reproductor `b485e332` (`TypeError: a.addOnDisposeCallback is not a function`); yt-dlp avisa de que "pueden faltar formatos". La descarga terminó bien. No depende de Windows (riesgo R-07) | **Abierto: decisión del Responsable.** Corregirlo exige actualizar la versión fijada de yt-dlp con el procedimiento de SUP-S01 (ADR-0002), fuera del alcance de la campaña (análisis abajo) |

### Análisis de T42-D3 con el espacio de análisis (`yt-dlp-gui-clone`)

- **Cómo lo resuelve la GUI de referencia (`upstream/source/yt-dlp-gui-kannagi`):** no trata los retos de JavaScript. Ejecuta un `yt-dlp.exe` externo que busca junto a la aplicación o en la ruta configurada (`Views/Main.xaml.cs`, `ScanDepends`; `Wrappers/DLP.cs`, `Exec`). El ejecutable oficial ya incluye yt-dlp-ejs, y cuando YouTube cambia, el usuario lo sustituye por uno más nuevo, sin tocar la GUI. Es decir: la respuesta a este defecto es actualizar yt-dlp.
- **Qué permite yt-dlp 2026.10.26 sin actualizarse (`upstream/source/yt-dlp-2026.10.26`):** la versión del script solucionador está fijada (`yt-dlp-ejs==0.8.0` en `pyproject.toml`). El componente remoto `ejs:github` descarga esa misma versión (`jsc/_builtin/ejs.py`, la URL usa `_SCRIPT_VERSION`), y cualquier script de otra versión mayor o menor se rechaza (`ejs.py`, comprobación de `version_tuple(...)[:2]`). Solo la opción de desarrollo `youtube-ejs:dev=true;script_version=…` lo salta, y no es apta para producción. Ninguna opción del proyecto puede corregirlo con la versión fijada.
- **Consecuencia:** en este proyecto yt-dlp es una librería fijada (ADR-0002), así que el equivalente a "sustituir el ejecutable" es el procedimiento de actualización SUP-S01: nueva versión fijada de yt-dlp (con su yt-dlp-ejs), pruebas de contrato, nuevo candidato.

### Documentación corregida

- El experimento tiene cuatro escenarios por estrategia más el control de asignación tardía de `job_object`; el guion y ADR-0029 decían "cinco escenarios" para `job_object`.
- En Windows, `pytest -m windows` selecciona 16 pruebas, no 10.

## Candidato `t42-candidate-2`

Pendiente: repetir sobre él el paso 3 completo y el paso 4, y continuar desde el paso 2 y el 5. Lo que no cambió (pasos 1 y 5.1) se conserva del candidato 1; los cambios de `t42-candidate-2` solo tocan una prueba, el experimento y la documentación, no el código del producto.
