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
| T42-D1 | 3 | *Prueba* | Menor (bloquea el paso 3 obligatorio hasta repetirlo) | `test_job_without_progress_is_terminated_with_its_child_after_the_grace_period` abría el handle del hijo **después** de que el árbol se terminara; el PID ya no existía y `OpenProcess` falló con `WinError 87`. Que el PID no existiera es coherente con que el hijo se terminó, pero la prueba no llegó a comprobarlo. En Linux pasaba porque el hijo quedaba como zombi un instante | Corregido después (ver abajo): el handle se abre antes de pedir la cancelación, con el hijo vivo |
| T42-D2 | 4 | *Herramienta de la campaña* (experimento) | Menor | Al terminar un escenario, la limpieza mataba los procesos que la estrategia deja vivos a propósito y borraba la carpeta temporal sin esperar a que salieran; en Windows `TerminateProcess` es asíncrono y el parcial seguía abierto (`PermissionError 13`). Se perdían esas observaciones, no las de `job_object` | Corregido después (ver abajo): la limpieza espera a que salgan y una carpeta retenida ya no descarta la observación |
| T42-D3 | 5.1 | *Producto, general* (externo: cambio de YouTube frente a yt-dlp 2026.10.26 y yt-dlp-ejs 0.8.0 fijados) | Mayor | El solucionador de retos `n` de yt-dlp-ejs falla en deno con el reproductor `b485e332` (`TypeError: a.addOnDisposeCallback is not a function`); yt-dlp avisa de que "pueden faltar formatos". La descarga terminó bien. No depende de Windows (riesgo R-07) | **Abierto: decisión del Responsable.** Corregirlo exige actualizar la versión fijada de yt-dlp con el procedimiento de SUP-S01 (ADR-0002), fuera del alcance de la campaña (análisis abajo) |

### Análisis de T42-D3 con el espacio de análisis (`yt-dlp-gui-clone`)

- **Cómo lo resuelve la GUI de referencia (`upstream/source/yt-dlp-gui-kannagi`):** no trata los retos de JavaScript. Ejecuta un `yt-dlp.exe` externo que busca junto a la aplicación o en la ruta configurada (`Views/Main.xaml.cs`, `ScanDepends`; `Wrappers/DLP.cs`, `Exec`). El ejecutable oficial ya incluye yt-dlp-ejs, y cuando YouTube cambia, el usuario lo sustituye por uno más nuevo, sin tocar la GUI. Es decir: la respuesta a este defecto es actualizar yt-dlp.
- **Qué permite yt-dlp 2026.10.26 sin actualizarse (`upstream/source/yt-dlp-2026.10.26`):** la versión del script solucionador está fijada (`yt-dlp-ejs==0.8.0` en `pyproject.toml`). El componente remoto `ejs:github` descarga esa misma versión (`jsc/_builtin/ejs.py`, la URL usa `_SCRIPT_VERSION`), y cualquier script de otra versión mayor o menor se rechaza (`ejs.py`, comprobación de `version_tuple(...)[:2]`). Solo la opción de desarrollo `youtube-ejs:dev=true;script_version=…` lo salta, y no es apta para producción. Ninguna opción del proyecto puede corregirlo con la versión fijada.
- **Consecuencia:** en este proyecto yt-dlp es una librería fijada (ADR-0002), así que el equivalente a "sustituir el ejecutable" es el procedimiento de actualización SUP-S01: nueva versión fijada de yt-dlp (con su yt-dlp-ejs), pruebas de contrato, nuevo candidato.

### Documentación corregida

- El experimento tiene cuatro escenarios por estrategia más el control de asignación tardía de `job_object`; el guion y ADR-0029 decían "cinco escenarios" para `job_object`.
- En Windows, `pytest -m windows` selecciona 16 pruebas, no 10.

## Correcciones posteriores y vigencia de la evidencia (2026-11-26)

No se crea `t42-candidate-2`: desde la versión 3.0 del guion, cada ejecución evalúa el `main` publicado y se identifica por su commit (ver el guion). La etiqueta `t42-candidate-1` y su evidencia se conservan.

| Defecto | Estado | Corrección |
|---|---|---|
| T42-D1 | Corregido; **confirmado en Windows** en la ejecución `20261125-214035-f3e041a1dafe` | El handle del hijo se abre antes de cancelar (`e5dce6e`) |
| T42-D2 | Corregido; **confirmado en Windows** en la ejecución `20261125-214035-f3e041a1dafe` | La limpieza del experimento espera a que salgan los procesos (`269472e`) |
| T42-D3 | **Resuelto: confirmado en Windows** en la ejecución `20261125-214035-f3e041a1dafe` | yt-dlp 2026.10.26 → **2026.11.23** con SUP-S01 ([procedimiento](../process/yt-dlp-update-procedure.md)); yt-dlp-ejs 0.8.0 y deno 2.9.8 no cambian. Prueba `network` nueva: `test_a_youtube_download_solves_its_javascript_challenges` |

**Evidencia técnica de la actualización (T42-D3).** El fallo ocurrió con el reproductor `player_ias.vflset/en_US/base.js`, la variante `main`, que era la predeterminada en 2026.10.26 (`_DEFAULT_PLAYER_JS_VARIANT = 'main'`). 2026.11.23 la cambia a `tv` (*Use `tv` as default `player_js_variant`*, yt-dlp #18124, en su Changelog; `_DEFAULT_PLAYER_JS_VARIANT = 'tv'` en el código), y su README documenta `tv` como predeterminada y las demás como variantes de depuración. Es la única versión estable posterior en PyPI (2026-11-23) y fija la misma yt-dlp-ejs 0.8.0, que sigue siendo la última publicada. Que el cambio de variante evite el fallo es una inferencia del código y del Changelog: el entorno de desarrollo no llega a YouTube, así que solo la ejecución en Windows lo confirma.

**Impacto sobre los contratos.** Comparando 2026.10.26 con el wheel instalado de 2026.11.23, son idénticos byte a byte `YoutubeDL.py` (orden `before_dl` → archivo existente → `fixup` → `post_process`, `download()`, `DownloadCancelled`, `prepare_filename`, `paths.temp`, mensaje de formato no disponible), los postprocessors (`common`, `ffmpeg`, `movefilesafterdownload`), los descargadores (`common`, `http`, `fragment`), los extractores `generic` y `common` (playlists perezosas) y el proveedor de retos (`jsc`). Cambian los clientes y la variante de YouTube, otros extractores ajenos al proyecto, `find_xpath_attr` y el rango del user agent. Las 549 pruebas de Linux pasan con la versión nueva, incluidas las de contrato contra la librería real.

### Qué evidencia de `t42-candidate-1` (`5f30151`) sigue valiendo

Desde `5f30151` no cambió el código de `workers/`, de las reclamaciones ni de `vendor/`.

| Evidencia | ¿Vigente? | Motivo | En la siguiente ejecución |
|---|---|---|---|
| Paso 1, instalación | En parte | `uv sync` instala ahora otra yt-dlp; el procedimiento de actualización del clon es nuevo | Se repite (paso 1) |
| Paso 3, `pytest -m windows` (16 pasadas) | Sí | Ni las pruebas ni el código que prueban cambiaron | Se repite de todos modos dentro de las suites, sin coste manual |
| Paso 3, suite completa | No | T42-D1 y yt-dlp | Se repite |
| Paso 3, `network` (3 pasadas) | No | Cambió yt-dlp | Se repite, con la prueba nueva de T42-D3 |
| Paso 4, los cuatro escenarios de `job_object` (*ninguno vivo*) | Sí | El terminador no cambió; el cambio del experimento solo afecta a la limpieza | Se repite para ver las cinco filas que faltaron (T42-D2) |
| Paso 5.1, primer `enqueue` | No | Cambió yt-dlp (extracción y formatos de YouTube) | Se repite completo |

### Pendiente en Windows

Pasos 2 (`diagnose`, ahora automático), 3, 4 (filas de T42-D2), 5.1 completo (unión, solo audio, duplicado), 5.2 a 5.7 (playlists, `--playlist`, `--keep-waiting` y concurrencia de dos terminales, cancelación, reintentos y purga, cola ocupada), 6 a 12 (procesos tras cancelar, cierres y `Ctrl+C`, recuperación y reanudación, cambio de formato, integridad, propiedad de archivos y concurrencia, consultas `list`/`show`, estado persistido) y 13 (memoria y SUP-P04). La validación de UC-01 a UC-10 no está completa.

## Ejecución `20261125-214035-f3e041a1dafe` (commit `f3e041a1dafed8a597a94c47bc4929ff8146065b`, 2026-11-25)

Primera ejecución con el guion 3.0, sobre el `main` publicado (`run.txt`: *commit is the published main: True*). Mismo equipo; PowerShell 7.6.9, uv 0.11.8, Python 3.12.13. Dependencias (`dependencies.log`): yt-dlp 2026.11.23, yt-dlp-ejs 0.8.0, deno 2.9.8. Evidencia: `C:\qmd-validation\runs\20261125-214035-f3e041a1dafe\` (entregada como `qmd-validation-251126215710.7z`); el JSON del experimento se copió a [t33-windows-results-f3e041a.json](../notes/experiments/t33-windows-results-f3e041a.json). Todos los códigos de salida de `exit-codes.txt` son 0.

| Paso | Resultado | Evidencia | Observaciones |
|---|---|---|---|
| 1 Actualización del clon e instalación | **pasa** | Consola; `environment.txt`, `dependencies.log` | El clon pasó de *detached HEAD* (etiqueta) a `main` con `git switch` y `git merge --ff-only`; `uv sync` cambió solo yt-dlp |
| 2 `diagnose` | **pasa** | `diagnose.log` | `[ OK ]` en ffmpeg (incluido), ffprobe, `yt-dlp 2026.11.23 with yt-dlp-ejs 0.8.0`, deno 2.9.8 y base de datos (esquema 4) |
| 3 Suites | **pasa** | `suite-*.log` | Cinco comprobaciones con código 0; `pytest`: 536 pasadas, 7 omitidas por diseño, 0 fallidas (T42-D1 confirmado); la protección de datos reales no informó cambios. `-m windows`: 16 pasadas. `-m network`: 4 pasadas, incluida la regresión de T42-D3 |
| 4 Experimento | **pasa** | `process-tree-termination.json` | Las 13 filas coinciden con lo esperado y ninguna es `ERROR` (T42-D2 confirmado): `job_object`, *ninguno vivo* en sus cuatro escenarios; el control de asignación tardía deja vivos al hijo y al nieto; `taskkill_tree` no encuentra a los descendientes de un worker caído ni sobrevive a la muerte del proceso principal |
| 5.1 Video, solo audio y duplicado | **pasa** | `queue-5.1.log`, cola `queues\5.1` | Job 1 `COMPLETED`, `395+251` unidos (AV1 + Opus, 19 s, 474 478 bytes); job 2 `COMPLETED` en `audio\`, Opus sin recodificar (19 s, 247 109 bytes); job 3 `SKIPPED`. Comprobados con `ffprobe`. `.partial` vacía; dos reclamaciones con el owner token de cada job; esquema 4 |

**T42-D3 resuelto.** El log de la cola 5.1 muestra que yt-dlp usó el mismo reproductor que falló el 2026-11-25 (`b485e332`), ahora en su variante `tv` (`Downloading player b485e332-tv`), resolvió los retos con deno (`Solving JS challenges using deno`) y no registró ninguna línea `WARNING` ni `ERROR`. La prueba `test_a_youtube_download_solves_its_javascript_challenges` también pasó.

### Paso 5.2 en la misma ejecución (consola del Evaluador; sin archivo de evidencia nuevo)

| Paso | Resultado | Evidencia | Observaciones |
|---|---|---|---|
| 5.2 Playlists | **pasa con defectos** | Salida de la consola; `queue-5.2.log` (parcial, código 1) | Dos playlists (URL con `si=`): 15 y 2 entradas, cada una en su carpeta con el índice delante; 15 descargas `COMPLETED` unidas por ffmpeg (`.webm` y `.mkv`); `show 1` resume `13 COMPLETED, 2 FAILED`; `list --parent 1` lista las 15 entradas. Nombres recortados por `max_filename_length` que pierden el `[id]` (jobs 7, 10, 16): el caso de R-14, sin colisión. **No se probó** el duplicado entre playlists (UC-04 A2): la segunda playlist no repetía ningún video |

| Id | Paso | Origen | Gravedad | Descripción | Estado |
|---|---|---|---|---|---|
| T42-D4 | 5.2 | *Producto, específico de Windows* (se reprodujo en Linux con `PYTHONIOENCODING=cp1252`) | Mayor | Con la salida redirigida (aquí, `Save-ValidationQueueState` y su `Tee-Object`), Python escribe en cp1252, que no tiene emojis: `list` terminó con `UnicodeEncodeError` en el título "…100% works 😎😎" y cortó la lista. Lo mismo habría cortado `run` a mitad de la cola con un título así | Corregido: los caracteres que la codificación no tiene se escriben como `?` (`__main__.replace_unencodable_output`); prueba `test_list_never_fails_on_characters_the_output_encoding_lacks`. **Pendiente de confirmar en Windows** |
| T42-D5 | 5.2 | *Documentación* (especificación) | Menor | Dos entradas de una playlist retiradas por YouTube (derechos de autor, normas) se crearon `PENDING` y fallaron al descargarse con `UNAVAILABLE`, y `run` terminó con código 1. UC-04 A3 decía que una entrada no disponible se crea `SKIPPED`, pero la lista de YouTube no las marcaba: saberlo exigiría resolver cada entrada y perder la iteración perezosa (ADR-0009). El comportamiento es el de UC-03 A2 | UC-04 A3 precisado: `SKIPPED` solo si el sitio la marca en la lista; si no, `FAILED` con `UNAVAILABLE` al descargar |
| T42-D6 | 5.2 | *Producto, general* | Menor | `show 1` mostraba `Title: -` y `list` la URL de la playlist, aunque la expansión conocía su título ("found 15 entries in playlist '…'") | Corregido: el primer lote da a la expansión el título de la playlist (`Job.record_playlist_title`); prueba `test_a_playlist_batch_gives_the_expansion_the_playlist_title`. **Pendiente de confirmar en Windows** |

### Pendiente en Windows tras esta ejecución

Confirmar T42-D4 y T42-D6 (repetir 5.2 en una ejecución nueva, con una segunda playlist que repita un video de la primera para UC-04 A2); pasos 5.3 a 5.7 (`--playlist`, `--keep-waiting` y dos terminales, cancelación, reintentos y purga, cola ocupada), 6 a 12 (procesos tras cancelar, cierres y `Ctrl+C`, reanudación tras un cierre forzado, cambio de formato, integridad, propiedad de archivos y concurrencia, estado persistido) y 13 (memoria y SUP-P04). La validación de UC-01 a UC-10 no está completa.

## Ejecución `20261125-222227-ddffe96cb470` (commit `ddffe96cb470658855e6702caf4618534297c99f`, 2026-11-25)

Consola del Evaluador; sin archivo de evidencia todavía. `Start-ValidationRun` y `diagnose` pasan (código 0; yt-dlp 2026.11.23 con yt-dlp-ejs 0.8.0, esquema 4).

| Paso | Resultado | Evidencia | Observaciones |
|---|---|---|---|
| 5.2 Playlists | **pasa con defectos** | `queue-5.2.log`, `queue-5.2-2.log` (código 0) | Las mismas dos playlists (15 y 2 entradas). 6 descargas `COMPLETED`; 2 `UNAVAILABLE` (los videos retirados de T42-D5, comportamiento ya documentado); 1 `UNKNOWN` (T42-D7) y 8 `NETWORK` por un corte de DNS del equipo (`getaddrinfo failed`), ajeno al producto. **T42-D4 confirmado**: `Save-ValidationQueueState` terminó con código 0 y los emojis salen como `?`. **T42-D6 confirmado**: `show 1` muestra el título de la playlist. **UC-04 A2 probado**: al volver a encolar las dos playlists (dos veces), sus 17 hijos se crearon `SKIPPED`, también los de descargas `FAILED`: una descarga fallida sigue siendo activa (SUP-R05, ADR-0012) y se recupera con `retry` sobre el job original. `New-ValidationQueue "5.2"` repetido se negó sin borrar nada |

| Id | Paso | Origen | Gravedad | Descripción | Estado |
|---|---|---|---|---|---|
| T42-D7 | 5.2 | *Producto, general* (contrato con yt-dlp) | Menor | Un timeout de conexión al servidor de video quedó como `UNKNOWN` en lugar de `NETWORK`. Cuando el downloader HTTP de yt-dlp agota los reintentos, lanza el `DownloadError` fuera de un bloque `except` (`FileDownloader.report_retry` → `YoutubeDL.trouble`): el error de red original se pierde y solo queda el texto `[download] Got error: …` | Corregido: ese texto se clasifica como `NETWORK` (`DOWNLOAD_RETRIES_EXHAUSTED_MESSAGE`); prueba de contrato con el código real de yt-dlp, `test_yt_dlp_download_retry_contract.py`, añadida al procedimiento de actualización. **Pendiente de confirmar en Windows** (requiere un corte de red durante una descarga; si no se reproduce, queda cubierto por la prueba de contrato) |
| T42-D8 | 5.2 | *Procedimiento de validación* | Menor | En la evidencia, las rayas (`—`) de los títulos salen como `�` y los emojis como `?`: Python escribe en cp1252 y PowerShell lee la tubería con otra codificación | Corregido en `Invoke-ValidationStep`: los programas escriben y PowerShell lee en UTF-8 durante cada paso. No se pudo ejecutar PowerShell en el entorno de desarrollo: **pendiente de confirmar en Windows** |

### Suites y pasos 5.3 y 5.4 en la misma ejecución (consola del Evaluador; evidencia sin las descargas pendiente de recibir)

| Paso | Resultado | Evidencia | Observaciones |
|---|---|---|---|
| 3 Suites | **pasa** | `suite-run-checks.log` (538 pasan, 7 omitidas, código 0), `suite-pytest-windows.log` (16, código 0), `suite-pytest-network.log` (4, código 0) | Incluye `test_output_encoding.py` y `test_youtube_challenge_solving.py` en Windows |
| 5.6 Reintentar y purgar | **no ejecutado** (T42-D9) | — | Las órdenes se ejecutaron sin cola activa, contra la carpeta de estado por omisión, `state\` dentro del clon de evaluación: estaba vacía (`No jobs`, `Purged 0 jobs`), así que no se cambió ningún dato; puede haber quedado ahí una base de datos vacía. Se repite sobre la cola 5.2, que conserva los 9 fallos |
| 5.3 `--playlist` | **pasa** | `queue-5.3.log` (código 0) | El job del video con `&list=` sin `--playlist` resolvió solo el video y quedó `SKIPPED` por duplicado (la playlist, encolada antes, ya lo tenía); con `--playlist`, la lista entera (15 entradas, todas `SKIPPED`). **UC-04 A2 entre playlists distintas**: "Functions (review)", en dos playlists, se descargó una vez (job 22) y la otra copia quedó `SKIPPED` (job 24). Las 9 descargas que fallaron por red en 5.2 terminaron bien, entre ellas la del título con emojis |
| 5.6 Reintentar y purgar (repetido sobre la cola 5.2) | **pasa** | `queue-5.6.log` (código 0) | `retry --all-failed` reencoló los 11 fallos (`attempt 2`); los 9 de red terminaron `COMPLETED` y los 2 retirados volvieron a fallar con `UNAVAILABLE`; `purge --completed` borró 54 jobs, conservó los archivos y la playlist 1, que aún tiene entradas fallidas |
| 5.5 Cancelar | **falla** (T42-D10) | `queue-5.5.log` (código 0) | A1/A5: `cancel 1` antes de `run` y `run` dio `Job 1: cancelled` sin descargar. A7: `cancel 6` de un job `COMPLETED` dio `already finished (COMPLETED); nothing to cancel`. **A4 falla**: ver T42-D10. El job 1 se lista como `EXPANSION`: un job empieza como expansión hasta saber si la URL es un solo contenido, y se canceló antes de resolverla |
| 5.4 `--keep-waiting` | **pasa** (falta confirmar en la evidencia que la playlist se encoló con `run` ya esperando) | `queue-5.4.log` (código 0) | `run --keep-waiting` tomó la playlist encolada desde otra ventana, la descargó y siguió esperando; un `Ctrl+C` terminó con código 130 |

| Id | Paso | Origen | Gravedad | Descripción | Estado |
|---|---|---|---|---|---|
| T42-D10 | 5.5 | *Producto, general* | Mayor | `cancel` de una playlist que ya había creado sus entradas respondió `Job 2 already finished (COMPLETED); nothing to cancel` y sus 13 entradas siguieron descargándose. La expansión termina en cuanto crea las entradas, así que UC-05 A4 solo funcionaba en los segundos de la expansión | Corregido: una playlist terminada con entradas no terminadas registra la cancelación de esas entradas (`CancelJob`, `entries_of_finished_playlists`); pruebas `test_cancelling_an_expanded_playlist_requests_its_unfinished_entries` y `test_cancel_of_an_expanded_playlist_cancels_its_unfinished_entries`; UC-05 A4 y el guion precisados. **Pendiente de confirmar en Windows** |
| T42-D9 | 5.6 | *Procedimiento de validación* | Menor | `Invoke-ValidationSuites` borra las variables de la cola para las pruebas y no las restablecía: las órdenes siguientes del programa usaron la carpeta de estado por omisión (`state\` del clon), fuera de la evidencia; en un clon de uso real habría sido la cola del usuario. El guion pedía volver a la cola 5.2 sin dar una forma de hacerlo | Corregido: las suites restablecen la cola activa, y `Use-ValidationQueue "<bloque>"` vuelve a una cola ya creada (también para la segunda ventana de 5.4, 5.5 y 5.7). **Pendiente de confirmar en Windows** |

### Pendiente en Windows tras esta ejecución

Las correcciones de T42-D7 a T42-D10 están en un commit posterior a `ddffe96`. Para no repetir pasos, la ejecución `20261125-222227-ddffe96cb470` sigue con los pasos 5.3 a 13 sin actualizar el clon; T42-D7 a T42-D10 se confirman en la siguiente ejecución (5.5 A4 se repite allí), junto con las correcciones que salgan de esos pasos.
