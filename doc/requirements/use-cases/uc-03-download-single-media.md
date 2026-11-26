# UC-03: Descargar un contenido

- **Objetivo:** los contenidos de la cola quedan descargados en la carpeta de destino sin que el User vigile cada descarga.
- **Actor principal:** User
- **Actor secundario:** Media site
- **Disparador:** el User ejecuta `run`.
- **Significativo para la arquitectura:** sí (recorre todos los componentes)
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: los escenarios originales están implementados; los ampliados tienen la marca de su flujo (`[estado: …]`).
- **Verificación:** escenarios implementados verificados con pruebas automáticas en desarrollo (Linux); validación en Windows pendiente de la campaña integral (T42 parcial, [registro](../../project-management/t42-results.md)).
- **Decisiones relacionadas:** [ADR-0008](../../notes/adr-0008-process-based-worker-pool.md), [ADR-0010](../../notes/adr-0010-sqlite-persistent-queue.md), [ADR-0013](../../notes/adr-0013-process-tree-terminator-abstraction.md)
- **Diseño:** [Parte 2, §1.2 y §1.3](../../design/02-flows-persistence-and-operations.md#13-descarga)

## Breve descripción

El User ejecuta la cola. El sistema toma un job pendiente, descubre que la URL es un solo contenido, lo descarga en un worker, une audio y video con ffmpeg si hace falta y registra el resultado.

## Precondiciones

- UC-01 completado (ffmpeg verificado).
- Hay al menos un job `PENDING` (UC-02).

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader run`.
2. El sistema recupera los jobs interrumpidos (UC-06) y verifica ffmpeg con el estado guardado.
3. El sistema arranca el pool con `worker_count` workers.
4. El sistema toma un job `EXPANSION` pendiente y lo envía a un worker libre; el job pasa a `RUNNING`.
5. El worker extrae la URL con el Media site y descubre que es un solo contenido; publica `SingleMediaFound`. El job pasa a `DOWNLOAD` y vuelve a `PENDING`.
6. El sistema vuelve a enviar el job a un worker; pasa a `RUNNING`.
7. El worker construye los parámetros de yt-dlp y la plantilla de salida, y empieza la descarga.
8. Antes de descargar, el worker publica `FormatSelected`; el sistema guarda `selected_format_id`.
9. Durante la descarga, el worker publica `DownloadProgressed` como máximo cada `progress_interval_seconds`; el sistema muestra el progreso en inglés.
10. Si el formato requiere unir audio y video, ffmpeg los une; el worker publica `PostprocessingProgressed`.
11. El worker publica `JobCompleted` con la ruta final; el job pasa a `COMPLETED`.
12. Cuando no quedan jobs pendientes, el sistema detiene el pool y termina con código `0`.

## Flujos alternativos

- **A1. Contenido duplicado** `[estado: divergente]` (paso 5): ya existe un job `DOWNLOAD` activo con la misma media key. El job queda `SKIPPED` y no se descarga. **Divergencia (D-16):** la identidad es la media key con el tipo de salida (audio o video), así que otra calidad, otro contenedor u otra carpeta del mismo contenido también quedan `SKIPPED`, en contra de la resolución aprobada de D-16, que admite las variantes ([BR-32](../business-rules.md), [análisis, §13.2](../requirements-analysis.md#132-identidad-variantes-y-duplicados)).
- **A2. Fallo de red, contenido no disponible, restricción geográfica o URL no soportada** `[estado: defecto]` (pasos 5 a 10; condiciones y motivos en el [catálogo de condiciones de fallo](../failure-conditions.md); **Defecto (R-28):** un fallo de almacenamiento que yt-dlp envuelve sin su `OSError` queda `UNKNOWN` en lugar de `FILESYSTEM`): el worker clasifica el error y publica `JobFailed` con su failure reason. El job pasa a `FAILED`; el resto de la cola continúa. Al terminar, el código de salida es `1`.
- **A3. Extractor desactualizado** `[estado: implementado]` (paso 5 o 7): igual que A2, con `EXTRACTOR_OUTDATED`; el mensaje indica que probablemente haga falta actualizar la versión fijada de yt-dlp.
- **A4. El worker muere sin publicar un evento final** `[estado: implementado]` (pasos 5 a 11): el pool lo detecta, publica `JobFailed(WORKER_CRASHED)` y arranca otro worker.
- **A5. `--keep-waiting`** `[estado: implementado]` (paso 12): el sistema no termina; espera jobs nuevos.
- **A6. Reciclado** `[estado: implementado]` (paso 11): el worker alcanzó `max_jobs_per_worker`; termina limpiamente y el pool arranca un reemplazo.
- **A7. El nombre final es de otro job, o ya existe un archivo que el job no escribió** `[estado: implementado]` (paso 7): plantilla sin `%(id)s`, título recortado, archivo del User o de un job purgado. El worker falla el job con `FILESYSTEM` antes de descargar, sin tocar ese archivo, y el mensaje indica moverlo o usar `%(id)s` ([ADR-0030](../../notes/adr-0030-final-file-ownership-claims.md)).
- **A8. La descarga no deja un archivo final utilizable** `[estado: implementado]` (paso 11): sin ruta, dentro de la carpeta de parciales, inexistente o vacío. El job pasa a `FAILED` con `FILESYSTEM` y la carpeta de parciales se conserva. Un `JobCompleted` de una descarga sin ruta nunca deja el job `COMPLETED` (contrato de `JobCompleted`).
- **A9. `Ctrl+C`** `[estado: implementado]` (pasos 4 a 11): interrupción, no cancelación; ver UC-05 A6.
- **A11. El Media site restringe las peticiones** `[estado: ausente]` (pasos 4 a 10): extendido por [UC-11](uc-11-preserve-jobs-under-external-conditions.md) A1. Hoy el job falla con `UNAVAILABLE` o `NETWORK` (A2).
- **A12. El equipo pierde la conexión** `[estado: ausente]` (pasos 4 a 10): extendido por [UC-11](uc-11-preserve-jobs-under-external-conditions.md) A2. Hoy el job y los siguientes fallan con `NETWORK` (A2).
- **A13. Falla el almacenamiento** `[estado: ausente]` (pasos 6 a 11): espacio, cuota, permisos, disponibilidad o uso compartido; extendido por [UC-17](uc-17-preserve-work-under-storage-failures.md). Hoy el job y los siguientes fallan con `FILESYSTEM` (A2).
- **A14. El User pausa o detiene la cola** `[estado: ausente]` (paso 4): ver [UC-14](uc-14-control-queue-execution.md).
- **A15. Fallo transitorio de la descarga** `[estado: divergente]` (pasos 8 a 10): HTTP 5xx, timeout o conexión cortada con un host. yt-dlp reintenta según [BR-07](../business-rules.md) antes de que el job falle con `NETWORK`. **Divergencia hoy:** la librería recibe 0 reintentos HTTP y 0 de fragmentos (R-24); en la campaña T42 un timeout hizo fallar un job a la primera.
- **A16. Resultados complementarios** `[estado: ausente]` (pasos 9 a 11): con las opciones de UC-02 A7, el job escribe además subtítulos, miniatura, descripción, metadatos o `info.json`, cada uno reclamado como resultado propio ([BR-31](../business-rules.md)). Todo resultado pedido es obligatorio salvo que el User lo marque como opcional ([BR-29](../business-rules.md)). Un opcional que el sitio no ofrece o que falla deja el job `COMPLETED` con la ausencia registrada; un obligatorio que falla deja el job `FAILED` y conserva los resultados ya publicados para reutilizarlos ([BR-30](../business-rules.md)).
- **A17. Varios resultados multimedia** `[estado: ausente]` (pasos 9 a 11; D-15 y D-18): con capítulos o secciones (UC-02 A8 y A11), el job produce N archivos. Termina `COMPLETED` cuando están todos los obligatorios; cada uno tiene su reclamación.
- **A18. SponsorBlock** `[estado: ausente]` (pasos 9 a 11; D-18): se consultan los segmentos al servicio de SponsorBlock (solo para YouTube; la petición envía un prefijo del hash del id del video). Quitar segmentos es un resultado pedido y, por tanto, obligatorio (BR-29). Si el servicio no responde tras sus reintentos, es una condición externa del servicio auxiliar: el multimedia descargado se conserva como resultado parcial y el postprocesamiento se repite después (UC-11; D-18), sin volver a descargar. Solo si el User marcó la eliminación como opcional, el job se completa sin quitar segmentos y lo registra. Si no hay segmentos, el resultado es el original y se informa.
- **A19. Contenedor o conversión** `[estado: ausente; condicionado]` (pasos 9 a 11; D-18): el remux y la conversión de audio usan ffmpeg sin pérdida o con el codificador pedido; recodificar el video solo es posible con los codificadores de la build incluida (§13.4 del análisis). Un fallo es `POSTPROCESSING` y conserva los parciales.
- **A10. Otro programa retiene la base de datos más allá de `busy_timeout`** `[estado: implementado]` (pasos 3 a 12): `run` avisa una vez por espera (`The queue is busy; waiting until another program releases it`) y repite la operación hasta que la cola queda libre; los workers siguen con sus jobs. Los comandos cortos, en cambio, terminan sin cambiar nada (UC-02 A3). Un segundo `Ctrl+C` detiene `run` también mientras espera. Observado en la validación en Windows (T42-D12): `run` terminaba con código `1` y dejaba el job `RUNNING`.

## Excepciones

Los fallos del job (A2, A3, A4, A7 y A8) terminan el job sin su objetivo; su tratamiento está en el [catálogo de condiciones de fallo](../failure-conditions.md).

- **E1. Transmisión en directo o programada** `[estado: ausente]` (pasos 5 a 10; D-10, [BR-24](../business-rules.md)): una programada (`live_status` «is_upcoming») vuelve a la cola sin ocupar un worker hasta su `release_timestamp`; una activa se descarga con yt-dlp con una duración máxima configurable; una interrumpida continúa desde el momento actual (salvo `live_from_start`) e informa de los tramos perdidos. Hoy no hay regla: el worker descarga sin límite (R-26).
- **E2. ffmpeg no supera la verificación de arranque** `[estado: implementado]` (paso 2): `run` termina con código `2` sin enviar jobs (ADR-0006).

## Postcondiciones

- **Éxito:** archivo final en `download_directory` (en su subcarpeta `audio` con `--audio-only`, o en la carpeta de su playlist); job `COMPLETED` con `output_path` y `selected_format_id`; la carpeta de parciales del job se borra; el job conserva la reclamación de su nombre final.
- **Fallo:** job `FAILED` con failure reason y mensaje; los archivos parciales quedan para reanudar (UC-06); si no dejó archivo final, suelta la reclamación de su nombre. Ningún archivo de otro job cambia.

## Requisitos especiales

- Ningún proceso de ffmpeg o deno sigue vivo al terminar `run`.
- Solo el proceso de `run` cambia el estado de los jobs; los workers solo publican job events.
- El progreso no se escribe en la base de datos.

## Reglas, requisitos y restricciones asociados

- **Reglas:** vigentes BR-13 (divergente de D-16), BR-17 y BR-22; aprobadas sin implementar BR-01, BR-05, BR-07, BR-08, BR-24, BR-25, BR-29 a BR-32, BR-41 y BR-43.
- **Requisitos suplementarios:** SUP-R02, SUP-R03, SUP-R04, SUP-R05, SUP-R11, SUP-P01, SUP-P03, SUP-U02, SUP-C04.
- **Restricciones:** solo el proceso de `run` cambia el estado de los jobs; el progreso no se guarda en la base de datos.
- **Dependencias:** UC-01, UC-02; extendido por UC-11, UC-14 y UC-17; UC-06 al arrancar.

## Criterios de aceptación

1. Con un servidor local, cada job `PENDING` termina `COMPLETED` con su archivo en la carpeta correcta, o `FAILED` con el motivo del catálogo.
2. Ningún proceso de ffmpeg o deno sigue vivo al terminar `run`.
3. Un fallo de un job no impide que los siguientes se completen.
4. Ningún archivo ajeno cambia (tamaño, fecha y SHA-256).

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Flujo completo con `ScriptedWorkerPool` (eventos predefinidos) | Cualquier sistema |
| Duplicado (A1) y clasificación de fallos (A2, A3) | Cualquier sistema |
| Pool real con contexto `spawn`, worker caído (A4) y reciclado (A6) | Cualquier sistema |
| Descarga de extremo a extremo contra un servidor HTTP local, con unión por ffmpeg | Cualquier sistema (ffmpeg del sistema) y **Windows** (ffmpeg incluido) |
| Memoria máxima del proceso principal, del worker y de ffmpeg | **Windows**, al cerrar la iteración |
| Descarga real de un video de YouTube (con deno) | **Windows**, manual |
| A7: el archivo final de otro job o del User no cambia (tamaño, fecha y SHA-256); dos jobs a la vez por un nombre | Cualquier sistema |
| A7 con mayúsculas, separadores, rutas de más de 260 caracteres y archivos abiertos | **Windows** (pruebas `windows`, campaña paso 11) |
