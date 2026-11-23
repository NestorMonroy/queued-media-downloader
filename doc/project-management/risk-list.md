# Lista de riesgos

- **Versión:** 1.0
- **Fecha:** 2026-11-23
- **Revisión:** al cerrar cada iteración

Exposición = probabilidad × impacto (1 bajo, 2 medio, 3 alto). Las iteraciones de Elaboración se ordenan para neutralizar primero los riesgos de mayor exposición.

| ID | Riesgo | Prob. | Impacto | Exposición | Mitigación | Iteración | Estado |
|---|---|---|---|---|---|---|---|
| R-01 | El pool de procesos con *spawn* no funciona como se diseñó (arranque, colas, reciclado, guard de `__main__`) | 2 | 3 | **6** | Pruebas con `get_context("spawn")` en cualquier sistema; ejecución real en Windows | E1 | Abierto |
| R-02 | ffmpeg o deno consumen más memoria de la aceptable en un equipo modesto | 2 | 3 | **6** | Medir RSS máxima en Windows; fijar SUP-P04 | E1 | Abierto |
| R-03 | Los binarios de ffmpeg incluidos no arrancan o no se resuelven bien desde `vendor/` (DLL, rutas) | 2 | 3 | **6** | Prueba `windows` de arranque; verificación de ADR-0006 | E1 | Abierto |
| R-04 | El Job Object no termina todo el árbol de procesos y quedan ffmpeg o deno huérfanos | 2 | 3 | **6** | `WindowsProcessTreeTerminator` mínimo con prueba `windows` sobre hijos y nietos | E2 | Abierto |
| R-05 | La reanudación falla porque la plantilla o el formato no coinciden con el primer intento | 2 | 2 | 4 | `selected_format_id` guardado; plantilla determinista; prueba de interrupción y reanudación | E2 | Abierto |
| R-06 | `process=False` no itera las playlists de forma perezosa y la memoria crece con su tamaño | 2 | 3 | **6** | Prueba con un canal grande (marcador `network`) | E3 | Abierto |
| R-07 | Un cambio de YouTube rompe la versión fijada de yt-dlp durante el desarrollo | 2 | 2 | 4 | Pruebas sin red (servidor HTTP local); procedimiento de actualización (SUP-S01) | Continuo | Abierto |
| R-08 | La cuota de Git LFS (10 GiB/mes en GitHub Free; ~151 MiB por clon) se agota | 1 | 2 | 2 | Sin CI; vigilar el consumo; revisar ADR-0005 si el proyecto crece | Transición | Abierto |
| R-09 | Una versión futura de ffmpeg supera 100 MiB en un archivo (`avcodec` mide hoy 89,7 MiB) | 1 | 1 | 1 | Git LFS; comprobar en cada actualización | Construcción | Abierto |
| R-10 | El antivirus bloquea archivos `.part` o rutas largas superan 260 caracteres | 2 | 2 | 4 | `file_access_retries`, `trim_file_name`, reglas con `PureWindowsPath`; verificación manual en Windows | E2 | Abierto |
| R-11 | Los errores específicos de Windows se detectan tarde (las pruebas `windows` solo se ejecutan al cerrar la iteración) | 2 | 2 | 4 | Adaptadores de Windows mínimos; iteraciones cortas | Continuo | Abierto |
| R-12 | Incumplimiento de licencias: LGPL de ffmpeg o material de `doc/reference/` sin licencia identificada | 1 | 2 | 2 | `LICENSE.txt` y `SOURCE.md` en `vendor/`; confirmar la licencia de las guías | E1 | Abierto |
