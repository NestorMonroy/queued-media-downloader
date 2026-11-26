# Guion de la campaña final de validación en Windows (T42)

- **Rol:** Evaluador en Windows ([caso de desarrollo](../process/development-case.md)).
- **Procedimiento y criterios:** [plan de E2, §7](iteration-plan-e2.md#7-campaña-final-de-validación-en-windows) y [§5](iteration-plan-e2.md#5-criterios-de-evaluación).
- **Qué se valida:** cada escenario de la [matriz de la §8](iteration-plan-e2.md#8-matriz-de-casos-de-uso-implementación-y-validación) marcado *Windows ⏳*.
- **Duración estimada:** medio día.
- **Versión del guion:** 2.0 (auditoría previa a la aceptación, T49, 2026-11-26).
- **Commit evaluado:** el que señala la etiqueta `t42-candidate-1` (o la `t42-candidate-N` vigente, §Corrección y regresión). El Responsable del proyecto la crea sobre `main` cuando la verificación de desarrollo pasa, y la anota aquí con su hash completo antes de la campaña: `t42-candidate-1 = <hash>`.

El Evaluador sigue los pasos en orden y anota cada resultado en el [registro](#registro-de-resultados) como **pasa**, **falla** o **no ejecutado** (con el motivo). Un paso no ejecutado nunca se anota como satisfactorio. No corrige el código: si un paso falla, guarda la salida y continúa con los pasos que no dependan de él. Cada fallo se convierte después en una tarea con su prueba de regresión, y el paso se repite.

## Criterios de aceptación de la campaña

- **Pasa** la campaña si todos los pasos pasan, o si cada fallo está clasificado (§Clasificación de defectos) como *no bloqueante* y el Responsable del proyecto acepta expresamente la desviación.
- **Falla** si algún paso marcado **obligatorio** falla (pasos 3, 6, 7, 8 y 11) o si hay un defecto *bloqueante* sin corregir.
- Cada paso indica su resultado esperado (**Se espera**). Un paso sin ejecutar se anota *no ejecutado*, con el motivo, y no cuenta como satisfactorio.
- La aceptación final la decide el Responsable del proyecto con el registro completo; la evidencia de Linux o de E1 no la sustituye.

## Requisitos previos

- Equipo físico con Windows 10 u 11 x64, con conexión a internet.
- Smart App Control desactivado ([ADR-0026](../notes/adr-0026-smart-app-control-precondition.md)).
- Git con Git LFS y uv instalados.
- Una carpeta de trabajo nueva. Todas las órdenes se ejecutan en PowerShell, en la carpeta del clon, salvo que se indique otra cosa.
- Ningún `config.toml` en la carpeta del clon (la suite se detiene si lo encuentra).

Para ver el estado de la cola en cualquier momento: `uv run queued-media-downloader list`.

## Entorno aislado

La campaña **nunca** usa ni borra la cola, la configuración ni la carpeta de descargas reales del Evaluador. Cada bloque usa una cola nueva en `C:\qmd-t42\<bloque>`, con las variables de entorno que el programa ya admite:

```powershell
. .\scripts\windows\t42_campaign.ps1     # carga las funciones de ayuda
New-CampaignQueue "5.1"                  # estado y descargas en C:\qmd-t42\5.1
```

Se usa una cola aislada en los pasos 2 y 5 a 12 (en el 5, una por bloque; en el 7, una por caso). `New-CampaignQueue` crea `C:\qmd-t42\<bloque>\state` y `C:\qmd-t42\<bloque>\downloads` (si ya existían, se detiene sin borrar nada) y fija `QUEUED_MEDIA_DOWNLOADER_STATE_DIRECTORY` y `QUEUED_MEDIA_DOWNLOADER_DOWNLOAD_DIRECTORY` en la sesión de PowerShell. Las rutas de este guion (`state\`, `.partial\job-1`, `audio\`) se refieren a esa cola. Al terminar, `C:\qmd-t42` se conserva como evidencia.

## Automatización

`scripts/windows/t42_campaign.ps1` automatiza lo repetitivo y deja la evidencia en `C:\qmd-t42\evidence`:

| Función | Qué hace |
|---|---|
| `Test-CampaignCommit "<hash>"` | Comprueba que el clon está limpio y en el commit evaluado; si no, se detiene |
| `Save-CampaignEnvironment` | Guarda versiones de Windows, Python, uv, git, git-lfs y el hash del commit |
| `New-CampaignQueue "<bloque>"` | Cola aislada (sección anterior) |
| `Invoke-CampaignSuites` | Paso 3: ejecuta `scripts/run_checks.py`, `pytest -m windows` y `pytest -m network`, cada uno con su salida completa en un archivo y su código de salida, sin tuberías que lo oculten |
| `Save-CampaignProcesses "<nombre>"` | Guarda `Get-Process ffmpeg, ffprobe, deno, python` (pasos 6 a 8) |

El script **no se ha ejecutado en el entorno de desarrollo** (Linux): su primera ejecución forma parte de la campaña, y un fallo del script se clasifica como defecto de herramienta de la campaña, no del producto.

## Pasos

### Paso 1. Instalación (UC-01, flujo básico; A7)

```powershell
git clone https://github.com/NestorMonroy/queued-media-downloader.git
cd queued-media-downloader
git checkout t42-candidate-1
git lfs pull
uv sync
. .\scripts\windows\t42_campaign.ps1
Test-CampaignCommit "<hash anotado arriba>"
Save-CampaignEnvironment
```

**Se espera:** los comandos terminan sin errores, `Test-CampaignCommit` confirma el commit y `vendor\` contiene los binarios reales, no punteros de LFS.

### Paso 2. Dependencias (UC-01, pasos 4 a 9; A1, A4, A5)

```powershell
New-CampaignQueue "2"
uv run queued-media-downloader diagnose
```

**Se espera:** `[ OK ]` en ffmpeg (la build incluida), ffprobe, deno y la base de datos (versión de esquema 3), y `Environment ready`.

### Paso 3. Suites automatizadas (criterios 1 y 2; obligatorio)

```powershell
Invoke-CampaignSuites
```

Equivale a ejecutar, cada uno con su código de salida:

```powershell
uv run python scripts/run_checks.py          # formato, linter, tipos, importaciones y pytest (stop-on-error)
uv run pytest -m windows
uv run pytest -m network
```

**Se espera:** todo pasa. Anotar, para cada `pytest`, el número de pruebas **pasadas, fallidas y omitidas por separado**, y que la sesión no informa `REAL USER DATA CHANGED`. Las 10 pruebas `windows` son: 4 del terminador de árboles de procesos (`tests/workers/test_process_tree_terminator.py`), 3 de la build de ffmpeg incluida (`tests/vendor/`) y 3 de reclamaciones de nombres finales (`tests/media_extraction/test_output_claims.py`: mayúsculas y separadores, archivo existente con otra capitalización, ruta de más de 260 caracteres con un archivo abierto). La suite normal incluye en Windows la prueba de interrupción real de la §5.1 (`tests/job_queue/test_real_interruption_recovery.py`) y las pruebas del terminador parametrizadas para la plataforma. Se omiten en Windows, por diseño, las 4 pruebas de `Ctrl+C` con señales POSIX (equivalente: paso 7), 2 del localizador de ffmpeg con un script POSIX y 1 de nombres que distinguen mayúsculas.

### Paso 4. Experimento de T33 (ADR-0029)

```powershell
uv run python scripts/experiments/process_tree_termination.py --json doc/notes/experiments/t33-windows-results.json
```

**Se espera:** para `job_object`, *ninguno vivo* en los cinco escenarios, también en `main_process_killed`. Pegar la tabla en el [documento del experimento](../notes/experiments/t33-process-tree-termination.md#resultados-en-windows), donde está el resultado esperado de cada estrategia.

### Paso 5. Casos de uso

Antes de cada bloque, partir de una cola vacía y aislada: `New-CampaignQueue "<número del bloque>"`. No borrar ninguna carpeta real.

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
uv run python -c "import os,sqlite3,time; c=sqlite3.connect(os.path.join(os.environ['QUEUED_MEDIA_DOWNLOADER_STATE_DIRECTORY'],'queue.sqlite3')); c.execute('BEGIN IMMEDIATE'); print('locked'); time.sleep(30)"
```

Mientras dice `locked`, en otra terminal: `uv run queued-media-downloader enqueue "<URL>"`.

**Se espera:** tras unos 5 s, `the queue is busy … no job was queued`, código `1`, y `list` sin el job nuevo. Repetir, mientras dure el bloqueo, con `cancel 1`, `retry 1` y `purge`: **se espera** `the queue is busy … nothing was changed`, código `1`, y la cola sin cambios.

### Paso 6. Procesos tras cancelar (UC-05 A2; R-04; obligatorio)

Encolar un video largo con unión de audio y video. Con `run` en marcha, en otra terminal, ejecutar `cancel 1` **mientras ffmpeg une los archivos** (la consola de `run` muestra la fase de unión). Después:

```powershell
Get-Process ffmpeg, deno, python -ErrorAction SilentlyContinue
```

**Se espera:** el job queda `CANCELLED` como mucho 10 s después (`cancellation_grace_seconds`); no queda ningún ffmpeg ni deno del job; el `.part` o las partes `.f<id>` se conservan en `.partial\job-1`.

### Paso 7. Cierres de `run` (UC-05 A6; UC-06; obligatorio)

Con un video largo descargándose en cada caso, y comprobando después procesos (paso 6) y estado (`list`):

| Caso | Acción | Se espera |
|---|---|---|
| a | Un `Ctrl+C` | `Interrupted`, código 130; el job sigue `RUNNING`; ningún proceso queda; el siguiente `run` lo reanuda |
| b | Dos `Ctrl+C` seguidos | `Stopped`, código 130, sin esperar; ningún proceso queda |
| c | `Ctrl+C` durante la unión de ffmpeg | ffmpeg no aborta por el `Ctrl+C`: el job sigue `RUNNING` y se reanuda, no queda `FAILED` |
| d | Cerrar la ventana de la terminal | Ningún proceso queda (Job Object); el siguiente `run` dice `Recovered 1 interrupted job` |
| e | `Stop-Process -Force` sobre el proceso `python` de `run` | Igual que d |
| f | Cinco o más `Ctrl+C` seguidos y rápidos | Código 130, sin traza de Python; como mucho un aviso `Already stopping; please wait`; ningún proceso queda; el job sigue `RUNNING` y el siguiente `run` lo reanuda |

### Paso 8. Interrupción real y reanudación (§5.1, obligatorio)

1. Confirmar que en el paso 3 pasó `tests/job_queue/test_real_interruption_recovery.py`.
2. Manual: encolar un video largo, `run`, y a mitad de la descarga `Stop-Process -Force` sobre `run` (caso e del paso 7). Anotar el tamaño del `.part` en `.partial\job-1`. Volver a ejecutar `run`.

**Se espera:** ningún proceso tras el cierre; el `.part` conserva su tamaño; el segundo `run` recupera el job y lo completa sin empezar de cero (lo descargado en el segundo `run` es aproximadamente el total menos el tamaño anotado).

### Paso 9. Cambio de formato al reanudar (UC-06 A1)

Interrumpir una descarga (paso 7, caso a). Con `run` parado, forzar un formato que ya no exista:

```powershell
uv run python -c "import os,sqlite3; c=sqlite3.connect(os.path.join(os.environ['QUEUED_MEDIA_DOWNLOADER_STATE_DIRECTORY'],'queue.sqlite3')); c.execute(\"UPDATE jobs SET selected_format_id='999999' WHERE id=1\"); c.commit()"
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

### Paso 11. Aislamiento entre jobs y propiedad de los archivos finales (R-14, ADR-0030; obligatorio)

Con una plantilla sin `%(id)s` que haga coincidir los nombres:

```powershell
$env:QUEUED_MEDIA_DOWNLOADER_SINGLE_MEDIA_OUTPUT_TEMPLATE = "video.%(ext)s"
uv run queued-media-downloader enqueue "<URL_A>" "<URL_B>"
uv run queued-media-downloader run --worker-count 2
Remove-Item Env:QUEUED_MEDIA_DOWNLOADER_SINGLE_MEDIA_OUTPUT_TEMPLATE
```

**Se espera:** un job `COMPLETED` y el otro `FAILED` con `FILESYSTEM` y un mensaje que nombra al dueño (`belongs to job N`); ninguno `COMPLETED` con el archivo del otro; el reintento de uno nunca borra los parciales del otro.

Después, en la misma cola:

1. Anotar tamaño, fecha y hash del archivo completado: `Get-FileHash <archivo>; Get-Item <archivo> | Select Length, LastWriteTimeUtc`.
2. Copiar a mano un archivo cualquiera como `VIDEO.MP4` (otra capitalización) en una cola nueva y encolar una URL con la misma plantilla. **Se espera:** `FAILED`, `already exists and was not written by this job`, y el archivo intacto.
3. Abrir el archivo completado con un reproductor y, mientras está abierto, encolar otro contenido con la misma plantilla y ejecutar `run`. **Se espera:** `FAILED` sin tocarlo.
4. `purge` y volver a encolar uno de los dos contenidos. **Se espera:** `FAILED` (`already exists`); el archivo, con el mismo tamaño, fecha y hash del punto 1.

### Paso 12. Estado persistido

Tras los pasos 6 a 9: `uv run queued-media-downloader list`.

**Se espera:** ningún job `RUNNING` o `CANCELLATION_REQUESTED` sin un `run` activo, salvo los que el siguiente `run` recupere (paso 7, casos a, d y e).

### Paso 13. Memoria (R-02, R-06, criterio 6, SUP-P04)

Usar el script del [paso 6 del guion de E1](evaluation-guide-e1.md#paso-6-medición-de-memoria-preparar-criterio-6) (ya corregido para medir el intérprete real) durante: una descarga con unión (paso 5.1), la expansión de una playlist grande (un canal con miles de videos) y una ejecución larga con reciclado de workers.

**Se espera:** picos de memoria anotados por proceso; la memoria del worker no crece con el número de entradas de la playlist. Con esos valores se fija SUP-P04.

## Registro de resultados

Commit evaluado: `t42-candidate-__` = `____________________` · Fecha: ________ · Evaluador: ________

| Paso | Resultado (pasa / falla / no ejecutado) | Evidencia | Observaciones (defectos `T42-D<n>`) |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | Pasadas / fallidas / omitidas de cada `pytest` | |
| 4 | | `t33-windows-results.json` | |
| 5.1 – 5.7 | | | |
| 6 | | Salida de `Get-Process` | |
| 7 a – f | | | |
| 8 | | Tamaño del `.part` antes y después | |
| 9 | | Salida de `show 1` | |
| 10 | | Salida de `ffprobe` | |
| 11 | | | |
| 12 | | Salida de `list` | |
| 13 | | Picos por proceso | |

## Clasificación de defectos

Cada fallo se registra con un identificador `T42-D<n>`, el paso, la salida guardada y esta clasificación:

| Campo | Valores |
|---|---|
| **Origen** | *Producto, específico de Windows* (no se reproduce en Linux); *Producto, general* (se reproduce en Linux: la verificación de desarrollo no lo cubría); *Prueba* (la prueba es incorrecta, el producto no); *Entorno* (red, antivirus, permisos, Smart App Control); *Herramienta de la campaña* (`t42_campaign.ps1`, este guion); *Documentación* |
| **Gravedad** | *Bloqueante*: pérdida o modificación de datos del User, procesos huérfanos, un job que queda en un estado incorrecto, un paso obligatorio que no se puede completar; *Mayor*: un escenario de un caso de uso no funciona, con alternativa; *Menor*: mensajes, formato, documentación |
| **Escenario afectado** | Caso de uso y flujo (por ejemplo, UC-05 A6) y requisito (por ejemplo, SUP-R02) |

Un defecto de *Entorno* se repite en un entorno corregido antes de clasificarlo como del producto. Ningún defecto se cierra sin la evidencia de su repetición.

## Corrección y regresión

1. El Agente de implementación crea una tarea por defecto del producto o de prueba, en su propia rama.
2. Escribe primero la prueba de regresión: automatizada en Linux si el defecto se reproduce allí; si es específico de Windows, una prueba `windows` (no ejecutable en desarrollo: se anota así, nunca como satisfactoria).
3. Corrige, ejecuta `scripts/run_checks.py` con stop-on-error e integra en `main` sin forzar nada.
4. El Responsable del proyecto crea la etiqueta siguiente, `t42-candidate-N`, sobre el nuevo commit.
5. El Evaluador repite, sobre ese commit: el paso 3 completo, los pasos donde aparecieron los defectos y los pasos que dependen del código cambiado (el Agente los indica en la tarea). El resto de los resultados se conserva si el cambio no los afecta.
6. El registro guarda los resultados de cada candidato por separado; la aceptación se decide sobre el último.

## Después de la campaña

El Responsable del proyecto actualiza la matriz de la §8 con la evidencia real, anota los hallazgos en la §6 del plan, actualiza la lista de riesgos y decide la aceptación final.
