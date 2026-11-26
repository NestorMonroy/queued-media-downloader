# Guion de la validación en Windows (campaña T42)

- **Rol:** Evaluador en Windows ([caso de desarrollo](../process/development-case.md)).
- **Procedimiento y criterios:** [plan de E2, §7](iteration-plan-e2.md#7-campaña-final-de-validación-en-windows) y [§5](iteration-plan-e2.md#5-criterios-de-evaluación).
- **Qué se valida:** cada escenario de la [matriz de la §8](iteration-plan-e2.md#8-matriz-de-casos-de-uso-implementación-y-validación) marcado *Windows ⏳*.
- **Duración estimada:** medio día.
- **Versión del guion:** 3.0 (2026-11-26). Las versiones 2.x evaluaban etiquetas `t42-candidate-N`; su evidencia se conserva en `C:\qmd-t42\`.
- **Qué se evalúa:** el estado publicado de `main`. Cada ejecución se identifica por el SHA completo del commit y su instante de arranque; no hace falta crear ni publicar etiquetas. `Start-ValidationRun` comprueba que el clon está limpio y en `origin/main`, y guarda en `run.txt` el commit, el `main` publicado, la rama y la fecha. Si el clon se mueve a otro commit, las funciones se niegan a seguir: los resultados de dos commits nunca se mezclan en una ejecución.

El Evaluador sigue los pasos en orden y anota cada resultado en el [registro](#registro-de-resultados) como **pasa**, **falla** o **no ejecutado** (con el motivo). Un paso no ejecutado nunca se anota como satisfactorio. No corrige el código: si un paso falla, guarda la salida y continúa con los pasos que no dependan de él. Cada fallo se convierte después en una tarea con su prueba de regresión, y el paso se repite.

## Criterios de aceptación de la campaña

- **Pasa** la campaña si todos los pasos pasan, o si cada fallo está clasificado (§Clasificación de defectos) como *no bloqueante* y el Responsable del proyecto acepta expresamente la desviación.
- **Falla** si algún paso marcado **obligatorio** falla (pasos 3, 6, 7, 8 y 11) o si hay un defecto *bloqueante* sin corregir.
- Cada paso indica su resultado esperado (**Se espera**). Un paso sin ejecutar se anota *no ejecutado*, con el motivo, y no cuenta como satisfactorio.
- La aceptación final la decide el Responsable del proyecto con el registro completo; la evidencia de Linux o de E1 no la sustituye.
- **Retos de JavaScript de YouTube (T42-D3):** ningún log de una cola debe contener `challenge solving failed` ni `Error solving`; la prueba `network` `test_a_youtube_download_solves_its_javascript_challenges` lo comprueba automáticamente.
- **Arranque de los workers en el Job Object (criterio explícito, T50):** durante toda la campaña, ningún `run` debe terminar con `could not start a worker`. Si ocurre, se guarda la salida y el log (`state\logs` de esa cola), se comprueba con `Save-ValidationProcesses` que no queda ningún proceso, y el siguiente `run` de esa cola debe recuperar los jobs `RUNNING` (`Recovered N interrupted job`). Un `run` que termina así sin dejar procesos y con la cola recuperable no es bloqueante; uno que deja procesos o jobs inconsistentes sí. La lógica independiente de Windows (reintento del arranque, apagado inmediato, código 1) está probada en Linux con dobles; el comportamiento nativo, solo aquí.

## Requisitos previos

- Equipo físico con Windows 10 u 11 x64, con conexión a internet.
- Smart App Control desactivado ([ADR-0026](../notes/adr-0026-smart-app-control-precondition.md)).
- Git con Git LFS y uv instalados.
- Una carpeta de trabajo nueva. Todas las órdenes se ejecutan en PowerShell, en la carpeta del clon, salvo que se indique otra cosa.
- Ningún `config.toml` en la carpeta del clon (la suite se detiene si lo encuentra).

Para ver el estado de la cola en cualquier momento: `uv run queued-media-downloader list`.

## Entorno aislado y evidencia

La validación **nunca** usa ni borra la cola, la configuración ni la carpeta de descargas reales del Evaluador, y ninguna función borra archivos. Cada ejecución vive en su propia carpeta:

```text
<raíz>\runs\<aaaammdd-hhmmss>-<commit de 12 caracteres>\
    run.txt          commit, main publicado, rama, fecha
    evidence\        entorno, dependencias, diagnose, salidas, códigos de salida, procesos, memoria
    queues\<bloque>\ una cola aislada por bloque (state\ y downloads\)
```

La raíz es, por orden: el parámetro `-EvidenceRoot` de `Start-ValidationRun`, la variable de entorno `QMD_VALIDATION_ROOT` o `C:\qmd-validation`. Repetir la validación tras una corrección crea otra carpeta en `runs\`; las anteriores se conservan.

`New-ValidationQueue "<bloque>"` crea la cola del bloque (si ya existe, se detiene sin borrar nada; para repetir, otro nombre, como `5.1-r2`) y fija `QUEUED_MEDIA_DOWNLOADER_STATE_DIRECTORY` y `QUEUED_MEDIA_DOWNLOADER_DOWNLOAD_DIRECTORY` en la sesión de PowerShell. Las rutas de este guion (`state\`, `.partial\job-1`, `audio\`) se refieren a la cola activa.

## Automatización

`scripts/windows/validation_campaign.ps1` automatiza lo repetitivo. No hay que editarlo para un commit nuevo: lo identifica al arrancar. Ningún archivo de evidencia se sobrescribe: una repetición crea `nombre-2.log`, `nombre-3.log`…

| Función | Qué hace | Evidencia |
|---|---|---|
| `Start-ValidationRun [-EvidenceRoot <ruta>] [-AllowUnpublishedCommit]` | Hace `git fetch`; se detiene si hay cambios locales, un `config.toml`, o si el clon no está en `origin/main` (salvo `-AllowUnpublishedCommit`, que lo registra como no publicado); crea la carpeta de la ejecución y guarda el entorno | `run.txt`, `environment.txt` (Windows, PowerShell, uv, Python, git, git-lfs), `dependencies.log` (`uv pip freeze`: yt-dlp, yt-dlp-ejs, deno…), `diagnose.log` (ffmpeg, ffprobe, yt-dlp, yt-dlp-ejs, deno y esquema) |
| `Resume-ValidationRun [-RunDirectory <ruta>]` | Retoma la ejecución en otra ventana (sin ruta, la más reciente) | — |
| `New-ValidationQueue "<bloque>"` | Cola aislada (sección anterior) | Carpeta `queues\<bloque>` |
| `Use-ValidationQueue "<bloque>"` | Vuelve a una cola ya creada: en una segunda ventana (tras `Resume-ValidationRun`) o para continuar un bloque | — |
| `Invoke-ValidationSuites` | `scripts/run_checks.py`, `pytest -m windows` y `pytest -m network`, cada uno con su código de salida real; borra de la sesión las variables de la cola | `suite-*.log`, `exit-codes.txt` |
| `Invoke-ProcessTreeExperiment` | Experimento de terminación de árboles de procesos (ADR-0029) | `process-tree-termination.log` y `.json` |
| `Invoke-ValidationStep "<nombre>" @("programa", "arg"…)` | Ejecuta un programa, muestra y guarda su salida y anota su código de salida real | `<nombre>.log`, `exit-codes.txt` |
| `Save-ValidationQueueState "<nombre>"` | Salida de `list` de la cola activa | `queue-<nombre>.log` |
| `Save-ValidationProcesses "<nombre>"` | Procesos `ffmpeg`, `ffprobe`, `deno` y `python` vivos | `processes-<nombre>.txt` |
| `Watch-ValidationMemory "<nombre>"` | Pico de memoria de cada proceso del programa hasta `Ctrl+C` (SUP-P04) | `memory-<nombre>.txt` |

**Automatizado:** identificación y comprobación del commit, entorno, versiones, `diagnose`, colas aisladas, suites, experimento, registro de salidas, códigos, procesos y memoria. **Manual:** las órdenes del programa de los pasos 5 a 12, `Ctrl+C`, cerrar ventanas, `Stop-Process`, archivos abiertos y el registro de resultados.

El script se revisó de forma estática en el entorno de desarrollo (Linux, sin PowerShell): sintaxis equilibrada, comandos del programa y de git que existen, rutas, variables de entorno, códigos de salida. Sus funciones heredan las de la versión anterior, ejecutadas en Windows el 2026-11-25; las nuevas (`Start-ValidationRun`, `Resume-ValidationRun`, `Invoke-ProcessTreeExperiment`, `Watch-ValidationMemory`) se ejecutan allí por primera vez, y un fallo suyo se clasifica como defecto de herramienta de validación.

## Pasos

### Paso 1. Obtener o actualizar el clon e instalar (UC-01, flujo básico; A7)

Un clon nuevo:

```powershell
git clone https://github.com/NestorMonroy/queued-media-downloader.git
cd queued-media-downloader
```

Un clon existente, aunque esté en *detached HEAD* (por ejemplo, tras evaluar una etiqueta): las órdenes no descartan cambios locales; si los hay, se detienen y hay que resolverlos antes.

```powershell
git status --short
git fetch origin
git switch main
git merge --ff-only origin/main
```

En los dos casos:

```powershell
git lfs pull
uv sync
. .\scripts\windows\validation_campaign.ps1
Start-ValidationRun
```

**Se espera:** los comandos terminan sin errores; `Start-ValidationRun` muestra el commit evaluado y la carpeta de la ejecución; `vendor\` contiene los binarios reales, no punteros de LFS.

### Paso 2. Dependencias (UC-01, pasos 4 a 9; A1, A4, A5)

`Start-ValidationRun` ya ejecutó `diagnose` en una cola aislada y lo guardó en `diagnose.log`.

**Se espera:** `[ OK ]` en ffmpeg (la build incluida), ffprobe, yt-dlp (`yt-dlp 2026.11.23 with yt-dlp-ejs 0.8.0`), deno y la base de datos (versión de esquema 4), y `Environment ready`; código 0 en `exit-codes.txt`.

### Paso 3. Suites automatizadas (criterios 1 y 2; obligatorio)

```powershell
Invoke-ValidationSuites
```

Equivale a ejecutar, cada uno con su código de salida:

```powershell
uv run python scripts/run_checks.py               # formato, linter, tipos, importaciones y pytest (stop-on-error)
uv run pytest -m windows -o addopts=
uv run pytest -m network -o addopts=
```

**Se espera:** todo pasa. Las 4 pruebas `network` (3 de expansión de YouTube y la regresión de T42-D3) están clasificadas como `BLOCKED_BY_ENVIRONMENT` en el entorno de desarrollo (su proxy rechaza YouTube con HTTP 403); en Windows, con acceso a internet, deben pasar. Si fallan, anotar la causa antes de clasificar el defecto (§Clasificación de defectos): un 403 o un bloqueo de red es *Entorno*. Anotar, para cada `pytest`, el número de pruebas **pasadas, fallidas y omitidas por separado**, y que la sesión no informa `REAL USER DATA CHANGED`. En Windows, `pytest -m windows` selecciona 16 pruebas: las 6 del terminador parametrizadas para la plataforma llevan allí también la marca `windows`, además de estas 10: 4 del terminador de árboles de procesos (`tests/workers/test_process_tree_terminator.py`), 3 de la build de ffmpeg incluida (`tests/vendor/`) y 3 de reclamaciones de nombres finales (`tests/media_extraction/test_output_claims.py`: mayúsculas y separadores, archivo existente con otra capitalización, ruta de más de 260 caracteres con un archivo abierto). La suite normal incluye en Windows la prueba de interrupción real de la §5.1 (`tests/job_queue/test_real_interruption_recovery.py`) y las pruebas del terminador parametrizadas para la plataforma. Se omiten en Windows, por diseño, las 4 pruebas de `Ctrl+C` con señales POSIX (equivalente: paso 7), 2 del localizador de ffmpeg con un script POSIX y 1 de nombres que distinguen mayúsculas.

### Paso 4. Experimento de terminación de árboles de procesos (T33, ADR-0029)

```powershell
Invoke-ProcessTreeExperiment
```

**Se espera:** para `job_object`, *ninguno vivo* en sus cuatro escenarios (`terminate_tree`, `isolation_other_tree_alive`, `worker_crashed_then_terminate` y `main_process_killed`); para el control `job_object_assigned_late`, hijo y nieto vivos; ninguna fila `ERROR`. Pegar la tabla en el [documento del experimento](../notes/experiments/t33-process-tree-termination.md#resultados-en-windows), donde está el resultado esperado de cada estrategia.

### Paso 5. Casos de uso

Antes de cada bloque, partir de una cola vacía y aislada: `New-ValidationQueue "<número del bloque>"`. Al terminar cada bloque: `Save-ValidationQueueState "<número del bloque>"`. No borrar ninguna carpeta real. Una orden del programa en una ventana sin cola activa usa la carpeta real del usuario: en la segunda ventana de 5.4, 5.5 y 5.7, ejecutar antes `Resume-ValidationRun` y `Use-ValidationQueue "<bloque>"`. `Invoke-ValidationSuites` deja activa la cola que había.

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
- Con `run` descargando una playlist en otra terminal: `cancel <id de la playlist>`. **Se espera:** `Cancellation requested for N unfinished playlist entries of job <id>`; la expansión sigue `COMPLETED` (terminó al crear las entradas), las entradas ya descargadas siguen `COMPLETED` y las demás quedan `CANCELLED`; `run` termina (A4).
- `cancel` de un job `COMPLETED`. **Se espera:** `already finished … nothing to cancel` (A7).

**5.6 Reintentar y purgar (UC-07, UC-10)**

```powershell
uv run queued-media-downloader retry --all-failed
uv run queued-media-downloader run
uv run queued-media-downloader purge --completed
uv run queued-media-downloader list
```

**Se espera:** los jobs reintentados muestran `queued again (attempt N)`; `purge` borra los terminados y conserva los archivos descargados.

**5.7 Base de datos bloqueada (UC-02 A3; UC-05 E2; UC-07 E3; UC-10)**

Cada orden debe tener algo que escribir: con nada que cambiar (`retry` de un job `PENDING`, `purge` sin jobs terminados), responde sin escribir y el bloqueo no la afecta. Antes del bloqueo, preparar un job `CANCELLED` (reintentable), uno `COMPLETED` (purgable) y uno `PENDING` (cancelable):

```powershell
uv run queued-media-downloader enqueue "https://www.youtube.com/watch?v=jNQXAC9IVRw"
uv run queued-media-downloader cancel 1
uv run queued-media-downloader enqueue "https://www.youtube.com/watch?v=HQ_FRYebb3o"
uv run queued-media-downloader run
uv run queued-media-downloader enqueue "https://www.youtube.com/watch?v=gqZRlHBPVVE"
uv run queued-media-downloader list
```

**Se espera:** job 1 `CANCELLED`, job 2 `COMPLETED`, job 3 `PENDING`.

En la segunda ventana (con la cola del bloque, `Use-ValidationQueue "5.7"`), retener un bloqueo de escritura durante 60 s:

```powershell
uv run python -c "import os,sqlite3,time; c=sqlite3.connect(os.path.join(os.environ['QUEUED_MEDIA_DOWNLOADER_STATE_DIRECTORY'],'queue.sqlite3')); c.execute('BEGIN IMMEDIATE'); print('locked'); time.sleep(60)"
```

Mientras dice `locked`, en la primera ventana:

```powershell
uv run queued-media-downloader enqueue "https://www.youtube.com/watch?v=0qXESF0jcBE"; $LASTEXITCODE
uv run queued-media-downloader cancel 3; $LASTEXITCODE
uv run queued-media-downloader retry 1; $LASTEXITCODE
uv run queued-media-downloader purge --completed; $LASTEXITCODE
```

**Se espera:** cada orden, tras unos 5 s, `the queue is busy … no job was queued` (`enqueue`) o `… nothing was changed` (las demás), y `1`. Al terminar el bloqueo, `list` igual que antes: 1 `CANCELLED`, 2 `COMPLETED`, 3 `PENDING`.

Tomar el bloqueo solo con `run` terminado. Con `run` en marcha, el caso es otro (UC-03 A10): **se espera** que `run` muestre `The queue is busy; waiting until another program releases it`, siga cuando termina el bloqueo y deje los jobs `COMPLETED`.

### Paso 6. Procesos tras cancelar (UC-05 A2; R-04; obligatorio)

Encolar un video largo con unión de audio y video. Con `run` en marcha, en otra terminal, ejecutar `cancel 1` **mientras ffmpeg une los archivos** (la consola de `run` muestra la fase de unión). Después:

```powershell
Save-ValidationProcesses "step6-after-cancel"
Save-ValidationQueueState "step6"
```

**Se espera:** el job queda `CANCELLED` como mucho 10 s después (`cancellation_grace_seconds`); no queda ningún ffmpeg ni deno del job; el `.part` o las partes `.f<id>` se conservan en `.partial\job-1`.

### Paso 7. Cierres de `run` (UC-05 A6; UC-06; obligatorio)

Una cola por caso (`New-ValidationQueue "7a"`, `"7b"`…). Tras cada caso: `Save-ValidationProcesses "step7<caso>"` y `Save-ValidationQueueState "step7<caso>"`.

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

En una segunda ventana de PowerShell, en la carpeta del clon:

```powershell
. .\scripts\windows\validation_campaign.ps1
Resume-ValidationRun
Watch-ValidationMemory "download-with-merge"
```

Mientras mide, en la primera ventana, ejecutar una descarga con unión (como en el paso 5.1); al terminar `run`, `Ctrl+C` en la segunda ventana. Repetir con otros nombres (`"large-playlist"`, `"worker-recycling"`) para la expansión de una playlist grande (un canal con miles de videos) y una ejecución larga con reciclado de workers. Es la misma medición que el [paso 6 del guion de E1](evaluation-guide-e1.md#paso-6-medición-de-memoria-preparar-criterio-6), ahora con su resultado guardado en la evidencia.

**Se espera:** picos de memoria anotados por proceso; la memoria del worker no crece con el número de entradas de la playlist. Con esos valores se fija SUP-P04.

## Registro de resultados

Los resultados reales de cada ejecución se registran en [t42-results.md](t42-results.md), una sección por commit evaluado; esta tabla es la plantilla.

Commit evaluado: `________________________________________` (de `run.txt`) · Carpeta de la ejecución: ________ · Fecha: ________ · Evaluador: ________

| Paso | Resultado (pasa / falla / no ejecutado) | Evidencia | Observaciones (defectos `T42-D<n>`) |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | Pasadas / fallidas / omitidas de cada `pytest` | |
| 4 | | `process-tree-termination.json` | |
| 5.1 – 5.7 | | | |
| 6 | | `processes-step6-after-cancel.txt` | |
| 7 a – f | | | |
| 8 | | Tamaño del `.part` antes y después | |
| 9 | | Salida de `show 1` | |
| 10 | | Salida de `ffprobe` | |
| 11 | | | |
| 12 | | Salida de `list` | |
| 13 | | `memory-*.txt` | |

## Clasificación de defectos

Cada fallo se registra con un identificador `T42-D<n>`, el paso, la salida guardada y esta clasificación:

| Campo | Valores |
|---|---|
| **Origen** | *Producto, específico de Windows* (no se reproduce en Linux); *Producto, general* (se reproduce en Linux: la verificación de desarrollo no lo cubría); *Prueba* (la prueba es incorrecta, el producto no); *Entorno* (red, antivirus, permisos, Smart App Control); *Herramienta de validación* (`validation_campaign.ps1`, `process_tree_termination.py`, este guion); *Documentación* |
| **Gravedad** | *Bloqueante*: pérdida o modificación de datos del User, procesos huérfanos, un job que queda en un estado incorrecto, un paso obligatorio que no se puede completar; *Mayor*: un escenario de un caso de uso no funciona, con alternativa; *Menor*: mensajes, formato, documentación |
| **Escenario afectado** | Caso de uso y flujo (por ejemplo, UC-05 A6) y requisito (por ejemplo, SUP-R02) |

Un defecto de *Entorno* se repite en un entorno corregido antes de clasificarlo como del producto. Ningún defecto se cierra sin la evidencia de su repetición.

## Corrección y regresión

1. El Agente de implementación crea una tarea por defecto del producto o de prueba, en su propia rama.
2. Escribe primero la prueba de regresión: automatizada en Linux si el defecto se reproduce allí; si es específico de Windows, una prueba `windows` (no ejecutable en desarrollo: se anota así, nunca como satisfactoria).
3. Corrige, ejecuta `scripts/run_checks.py` con stop-on-error, integra en `main` sin forzar nada y publica.
4. El Agente indica en el registro qué evidencia anterior sigue valiendo y qué pasos hay que repetir: el paso 3 completo, los pasos donde aparecieron los defectos y los que dependen del código o de las dependencias que cambiaron.
5. El Evaluador actualiza su clon a `main` (paso 1) y hace una ejecución nueva con `Start-ValidationRun`; solo repite los pasos indicados. No se crean etiquetas.
6. El registro guarda los resultados de cada commit por separado; la aceptación se decide sobre el último commit evaluado, con la evidencia vigente de los anteriores.

## Después de la campaña

El Responsable del proyecto actualiza la matriz de la §8 con la evidencia real, anota los hallazgos en la §6 del plan, actualiza la lista de riesgos y decide la aceptación final.
