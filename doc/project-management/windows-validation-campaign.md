# Guion de la campaña final de validación en Windows (T42)

- **Rol:** Evaluador en Windows ([caso de desarrollo](../process/development-case.md)).
- **Procedimiento y criterios:** [plan de E2, §7](iteration-plan-e2.md#7-campaña-final-de-validación-en-windows) y [§5](iteration-plan-e2.md#5-criterios-de-evaluación).
- **Qué se valida:** cada escenario de la [matriz de la §8](iteration-plan-e2.md#8-matriz-de-casos-de-uso-implementación-y-validación) marcado *Windows ⏳*.
- **Duración estimada:** medio día.

El Evaluador sigue los pasos en orden y anota cada resultado en el [registro](#registro-de-resultados) como **pasa**, **falla** o **no ejecutado** (con el motivo). Un paso no ejecutado nunca se anota como satisfactorio. No corrige el código: si un paso falla, guarda la salida y continúa con los pasos que no dependan de él. Cada fallo se convierte después en una tarea con su prueba de regresión, y el paso se repite.

## Requisitos previos

- Equipo físico con Windows 10 u 11 x64, con conexión a internet.
- Smart App Control desactivado ([ADR-0026](../notes/adr-0026-smart-app-control-precondition.md)).
- Git con Git LFS y uv instalados.
- Una carpeta de trabajo nueva. Todas las órdenes se ejecutan en PowerShell, en la carpeta del clon, salvo que se indique otra cosa.

Para ver el estado de la cola en cualquier momento: `uv run queued-media-downloader list`.

## Pasos

### Paso 1. Instalación (UC-01, flujo básico; A7)

```powershell
git clone https://github.com/NestorMonroy/queued-media-downloader.git
cd queued-media-downloader
git lfs pull
uv sync
```

**Se espera:** los cuatro comandos terminan sin errores y `vendor\` contiene los binarios reales, no punteros de LFS.

### Paso 2. Dependencias (UC-01, pasos 4 a 9; A1, A4, A5)

```powershell
uv run queued-media-downloader diagnose
```

**Se espera:** `[ OK ]` en ffmpeg (la build incluida), ffprobe, deno y la base de datos (versión de esquema 3), y `Environment ready`.

### Paso 3. Suites automatizadas (criterios 1 y 2)

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run lint-imports
uv run pytest
uv run pytest -m windows
uv run pytest -m network
```

**Se espera:** todo pasa. Anotar, para cada `pytest`, el número de pruebas **pasadas, fallidas y omitidas por separado**. Las pruebas `windows` incluyen las 10 del terminador de árboles de procesos (`tests/workers/test_process_tree_terminator.py`); la suite normal incluye en Windows la prueba de interrupción real de la §5.1 (`tests/job_queue/test_real_interruption_recovery.py`). Las dos pruebas de `Ctrl+C` con señales POSIX se omiten en Windows: su equivalente es el paso 7.

### Paso 4. Experimento de T33 (ADR-0029)

```powershell
uv run python scripts/experiments/process_tree_termination.py --json doc/notes/experiments/t33-windows-results.json
```

**Se espera:** para `job_object`, *ninguno vivo* en los cinco escenarios, también en `main_process_killed`. Pegar la tabla en el [documento del experimento](../notes/experiments/t33-process-tree-termination.md#resultados-en-windows), donde está el resultado esperado de cada estrategia.

### Paso 5. Casos de uso

Antes de cada bloque, partir de una cola vacía: borrar la carpeta `state\` del clon y la carpeta de descargas (`$HOME\Downloads\queued-media-downloader`).

**5.1 Video con unión de audio y video, como solo audio y duplicado (UC-02, UC-03; A1)**

```powershell
uv run queued-media-downloader enqueue "https://www.youtube.com/watch?v=jNQXAC9IVRw"
uv run queued-media-downloader enqueue --audio-only "https://www.youtube.com/watch?v=jNQXAC9IVRw"
uv run queued-media-downloader enqueue "https://www.youtube.com/watch?v=jNQXAC9IVRw"
uv run queued-media-downloader run
uv run queued-media-downloader list
```

**Se espera:** el primer job termina con un archivo unido, el segundo en `audio\`, el tercero `SKIPPED`. Ninguna carpeta `.partial\job-N` queda con contenido.

**5.2 Playlist (UC-04; A2, A3; criterio 3)**

Elegir una playlist pública pequeña (5 a 15 videos) y otra que repita uno de sus videos.

```powershell
uv run queued-media-downloader enqueue "https://www.youtube.com/playlist?list=<LISTA>"
uv run queued-media-downloader enqueue "https://www.youtube.com/playlist?list=<OTRA_LISTA>"
uv run queued-media-downloader run
uv run queued-media-downloader show 1
uv run queued-media-downloader list --parent 1
```

**Se espera:** una carpeta por playlist, con los archivos numerados; el video repetido descargado una sola vez y su otra copia `SKIPPED`; `show 1` resume las entradas por estado.

**5.3 Video dentro de una lista (`--playlist`, ADR-0027)**

```powershell
uv run queued-media-downloader enqueue "https://www.youtube.com/watch?v=<VIDEO>&list=<LISTA>"
uv run queued-media-downloader enqueue --playlist "https://www.youtube.com/watch?v=<VIDEO>&list=<LISTA>"
uv run queued-media-downloader run
```

**Se espera:** el primer job descarga solo el video; el segundo, la lista entera (el video aparece como duplicado).

**5.4 `--keep-waiting` y dos terminales (UC-03 A5; UC-02 A2)**

En una terminal: `uv run queued-media-downloader run --keep-waiting`. En otra: `uv run queued-media-downloader enqueue "<URL>"`.

**Se espera:** `run` descarga el job sin reiniciarse y sigue esperando. Terminarlo con `Ctrl+C` (código 130).

**5.5 Cancelar (UC-05; A1, A4, A5, A7)**

- Con `run` parado: encolar una URL, `cancel 1`, `run`. **Se espera:** `Job 1: cancelled` sin descargar nada (A1, A5).
- Con `run` descargando una playlist en otra terminal: `cancel <id de la playlist>`. **Se espera:** la expansión y sus entradas sin terminar quedan `CANCELLED` (A4).
- `cancel` de un job `COMPLETED`. **Se espera:** `already finished … nothing to cancel` (A7).

**5.6 Reintentar y purgar (UC-07, UC-10)**

```powershell
uv run queued-media-downloader retry --all-failed
uv run queued-media-downloader run
uv run queued-media-downloader purge --completed
uv run queued-media-downloader list
```

**Se espera:** los jobs reintentados muestran `queued again (attempt N)`; `purge` borra los terminados y conserva los archivos descargados.

**5.7 Base de datos bloqueada (UC-02 A3)**

En una terminal, abrir la base de datos y retener un bloqueo de escritura:

```powershell
uv run python -c "import sqlite3,time; c=sqlite3.connect('state/queue.sqlite3'); c.execute('BEGIN IMMEDIATE'); print('locked'); time.sleep(30)"
```

Mientras dice `locked`, en otra terminal: `uv run queued-media-downloader enqueue "<URL>"`.

**Se espera:** tras unos 5 s, `the queue is busy … no job was queued`, código `1`, y `list` sin el job nuevo.

### Paso 6. Procesos tras cancelar (UC-05 A2; R-04)

Encolar un video largo con unión de audio y video. Con `run` en marcha, en otra terminal, ejecutar `cancel 1` **mientras ffmpeg une los archivos** (la consola de `run` muestra la fase de unión). Después:

```powershell
Get-Process ffmpeg, deno, python -ErrorAction SilentlyContinue
```

**Se espera:** el job queda `CANCELLED` como mucho 10 s después (`cancellation_grace_seconds`); no queda ningún ffmpeg ni deno del job; el `.part` o las partes `.f<id>` se conservan en `.partial\job-1`.

### Paso 7. Cierres de `run` (UC-05 A6; UC-06)

Con un video largo descargándose en cada caso, y comprobando después procesos (paso 6) y estado (`list`):

| Caso | Acción | Se espera |
|---|---|---|
| a | Un `Ctrl+C` | `Interrupted`, código 130; el job sigue `RUNNING`; ningún proceso queda; el siguiente `run` lo reanuda |
| b | Dos `Ctrl+C` seguidos | `Stopped`, código 130, sin esperar; ningún proceso queda |
| c | `Ctrl+C` durante la unión de ffmpeg | ffmpeg no aborta por el `Ctrl+C`: el job sigue `RUNNING` y se reanuda, no queda `FAILED` |
| d | Cerrar la ventana de la terminal | Ningún proceso queda (Job Object); el siguiente `run` dice `Recovered 1 interrupted job` |
| e | `Stop-Process -Force` sobre el proceso `python` de `run` | Igual que d |

### Paso 8. Interrupción real y reanudación (§5.1, obligatorio)

1. Confirmar que en el paso 3 pasó `tests/job_queue/test_real_interruption_recovery.py`.
2. Manual: encolar un video largo, `run`, y a mitad de la descarga `Stop-Process -Force` sobre `run` (caso e del paso 7). Anotar el tamaño del `.part` en `.partial\job-1`. Volver a ejecutar `run`.

**Se espera:** ningún proceso tras el cierre; el `.part` conserva su tamaño; el segundo `run` recupera el job y lo completa sin empezar de cero (lo descargado en el segundo `run` es aproximadamente el total menos el tamaño anotado).

### Paso 9. Cambio de formato al reanudar (UC-06 A1)

Interrumpir una descarga (paso 7, caso a). Con `run` parado, forzar un formato que ya no exista:

```powershell
uv run python -c "import sqlite3; c=sqlite3.connect('state/queue.sqlite3'); c.execute(\"UPDATE jobs SET selected_format_id='999999' WHERE id=1\"); c.commit()"
uv run queued-media-downloader run
uv run queued-media-downloader show 1
```

**Se espera:** el job termina `COMPLETED` con un formato nuevo en `show 1`, y `.partial\job-1` ya no existe.

### Paso 10. Integridad

Para cada archivo descargado en los pasos 5 a 9:

```powershell
& .\vendor\ffmpeg\n9.0.2-39-g7adfbe40dc-win64-lgpl-shared\bin\ffprobe.exe -v error -show_entries format=duration,size -of default=nw=1 "<archivo>"
```

**Se espera:** cada archivo se abre y tiene duración y tamaño coherentes con el original.

### Paso 11. Aislamiento entre jobs (R-14)

Con una plantilla sin `%(id)s` que haga coincidir los nombres:

```powershell
$env:QUEUED_MEDIA_DOWNLOADER_SINGLE_MEDIA_OUTPUT_TEMPLATE = "video.%(ext)s"
uv run queued-media-downloader enqueue "<URL_A>" "<URL_B>"
uv run queued-media-downloader run --worker-count 2
Remove-Item Env:QUEUED_MEDIA_DOWNLOADER_SINGLE_MEDIA_OUTPUT_TEMPLATE
```

**Se espera:** un job `COMPLETED` y el otro `FAILED` con `already belongs to another job`; ninguno `COMPLETED` con el archivo del otro; el reintento de uno nunca borra los parciales del otro.

### Paso 12. Estado persistido

Tras los pasos 6 a 9: `uv run queued-media-downloader list`.

**Se espera:** ningún job `RUNNING` o `CANCELLATION_REQUESTED` sin un `run` activo, salvo los que el siguiente `run` recupere (paso 7, casos a, d y e).

### Paso 13. Memoria (R-02, R-06, criterio 6, SUP-P04)

Usar el script del [paso 6 del guion de E1](evaluation-guide-e1.md#paso-6-medición-de-memoria-preparar-criterio-6) (ya corregido para medir el intérprete real) durante: una descarga con unión (paso 5.1), la expansión de una playlist grande (un canal con miles de videos) y una ejecución larga con reciclado de workers.

**Se espera:** picos de memoria anotados por proceso; la memoria del worker no crece con el número de entradas de la playlist. Con esos valores se fija SUP-P04.

## Registro de resultados

| Paso | Resultado (pasa / falla / no ejecutado) | Evidencia | Observaciones |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | Pasadas / fallidas / omitidas de cada `pytest` | |
| 4 | | `t33-windows-results.json` | |
| 5.1 – 5.7 | | | |
| 6 | | Salida de `Get-Process` | |
| 7 a – e | | | |
| 8 | | Tamaño del `.part` antes y después | |
| 9 | | Salida de `show 1` | |
| 10 | | Salida de `ffprobe` | |
| 11 | | | |
| 12 | | Salida de `list` | |
| 13 | | Picos por proceso | |

## Después de la campaña

El Responsable del proyecto actualiza la matriz de la §8 con la evidencia real, anota los hallazgos en la §6 del plan, actualiza la lista de riesgos y decide la aceptación final.
