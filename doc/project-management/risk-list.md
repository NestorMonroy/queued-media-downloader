# Lista de riesgos

- **Versión:** 1.1 (cierre de E1)
- **Fecha:** 2026-11-23
- **Revisión:** al cerrar cada iteración

Exposición = probabilidad × impacto (1 bajo, 2 medio, 3 alto). Las iteraciones de Elaboración se ordenan para neutralizar primero los riesgos de mayor exposición.

| ID | Riesgo | Prob. | Impacto | Exposición | Mitigación | Iteración | Estado |
|---|---|---|---|---|---|---|---|
| R-01 | El pool de procesos con *spawn* no funciona como se diseñó (arranque, colas, reciclado, guard de `__main__`) | 2 | 3 | **6** | Pruebas con `get_context("spawn")` en cualquier sistema; colas de salida por worker, para que un worker caído no bloquee a los demás (T20); ejecución real en Windows | E1 | Mitigado (E1: pool y caída de worker probados en Windows) |
| R-02 | ffmpeg o deno consumen más memoria de la aceptable en un equipo modesto | 2 | 3 | **6** | Medir RSS máxima en Windows; fijar SUP-P04 | E2 | Abierto (medición trasladada desde E1) |
| R-03 | Los binarios de ffmpeg incluidos no arrancan o no se resuelven bien desde `vendor/` (DLL, rutas) | 2 | 3 | **6** | Prueba `windows` de arranque; verificación de ADR-0006 | E1 | Mitigado (E1: pruebas `windows` y unión real con la build incluida) |
| R-04 | El Job Object no termina todo el árbol de procesos y quedan ffmpeg o deno huérfanos | 2 | 3 | **6** | `WindowsProcessTreeTerminator` mínimo con prueba `windows` sobre hijos y nietos | E2 | Abierto (T33: hoy el pool solo termina el worker y sus descendientes siguen escribiendo, medido en Linux; propuesta en [ADR-0029](../notes/adr-0029-process-tree-termination-on-windows.md)) |
| R-05 | La reanudación falla porque la plantilla o el formato no coinciden con el primer intento | 2 | 2 | 4 | `selected_format_id` guardado; plantilla determinista; prueba de interrupción y reanudación | E2 | Abierto (T32: reanudación con `.part` y reintento de formato probados; falta la interrupción real, [plan de E2, §5.1](iteration-plan-e2.md#51-criterio-obligatorio-de-integración-entre-los-slices-b-y-c)) |
| R-06 | `process=False` no itera las playlists de forma perezosa y la memoria crece con su tamaño | 2 | 3 | **6** | Prueba con un canal grande (marcador `network`) | E2 | Abierto |
| R-07 | Un cambio de YouTube rompe la versión fijada de yt-dlp durante el desarrollo | 2 | 2 | 4 | Pruebas sin red (servidor HTTP local); procedimiento de actualización (SUP-S01) | Continuo | Abierto |
| R-08 | La cuota de Git LFS (10 GiB/mes en GitHub Free; ~151 MiB por clon) se agota | 1 | 2 | 2 | Sin CI; vigilar el consumo; revisar ADR-0005 si el proyecto crece | Transición | Abierto |
| R-09 | Una versión futura de ffmpeg supera 100 MiB en un archivo (`avcodec` mide hoy 89,7 MiB) | 1 | 1 | 1 | Git LFS; comprobar en cada actualización | Construcción | Abierto |
| R-10 | El antivirus bloquea archivos `.part` o rutas largas superan 260 caracteres | 2 | 2 | 4 | `file_access_retries`, `trim_file_name`, reglas con `PureWindowsPath`; verificación manual en Windows | E2 | Abierto |
| R-11 | Los errores específicos de Windows se detectan tarde (las pruebas `windows` solo se ejecutan al cerrar la iteración) | 2 | 2 | 4 | Adaptadores de Windows mínimos; iteraciones cortas | Continuo | Abierto |
| R-12 | Incumplimiento de la LGPL de ffmpeg (el material de `doc/reference/` quedó resuelto en [ADR-0025](../notes/adr-0025-reference-material-distribution.md)) | 1 | 2 | 2 | `LICENSE.txt` y `SOURCE.md` en `vendor/ffmpeg/` | E1 | Mitigado (E1: `LICENSE.txt` y `SOURCE.md`) |
| R-13 | Smart App Control impide ejecutar el proyecto: uv, la build de ffmpeg y otros binarios no están firmados (detectado en T19) | 2 | 3 | **6** | Precondición documentada en UC-01 ([ADR-0026](../notes/adr-0026-smart-app-control-precondition.md)); evaluar firma de código o un instalador firmado al planificar la distribución | Transición | Abierto |
| R-14 | Dos jobs distintos comparten nombre base de archivo (título largo recortado por `max_filename_length` que pierde el `[id]`, plantilla sin `%(id)s`, mismo id en dos extractores): sus archivos finales se pisan y la limpieza de A1 podría borrar un parcial del otro (detectado en T32) | 1 | 2 | 2 | La limpieza solo borra los nombres del formato abandonado; Windows no deja borrar un `.part` abierto; nunca se toca un archivo terminado ([ADR-0010, seguimiento de T32](../notes/adr-0010-sqlite-persistent-queue.md#seguimiento-de-t32-reanudación-verificada-2026-11-25)). Pendiente: decidir si la plantilla debe conservar siempre el `[id]` | Construcción | Abierto |
