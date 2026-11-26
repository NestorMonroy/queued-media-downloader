# UC-16: Preparar un informe de diagnóstico

- **Objetivo:** el User entrega al Mantenedor, en un solo archivo seguro para compartir, todo lo necesario para entender un problema (entorno, versiones, configuración, estado de la cola, fallos recientes y log) sin copiar consolas ni exponer credenciales.
- **Actor principal:** User
- **Actor secundario:** Mantenedor (recibe el informe)
- **Disparador:** algo no funciona y el User quiere reportarlo.
- **Prioridad:** baja
- **Significativo para la arquitectura:** no (reutiliza `diagnose` y el log)
- **Estado:** propuesto; **no implementado**.
- **Origen:**
  - **VoiceStudio:** "Save diagnostic bundle" (`backend/core/diagnostic_bundle.py`: autodiagnóstico, diario de errores clasificados, final del log, todo limpiado de datos sensibles).
  - **Seal:** "copy error report" y la pantalla de fallos.
  - **Campaña T42:** el empaquetado manual de la evidencia (VUC-07).

## Breve descripción

`report` genera un `.zip` en la carpeta de estado con:
- el resultado de `diagnose`;
- las versiones;
- la configuración efectiva sin valores sensibles;
- un resumen de la cola por estado;
- los últimos fallos con su motivo;
- el final del log.

Todo pasa por una limpieza de datos sensibles. La evidencia de validación (VUC-07) reutiliza la misma capacidad en lugar de duplicarla.

## Precondiciones

- UC-01 completado. La base de datos puede no abrirse: el informe lo registra.

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader report`.
2. El sistema ejecuta las comprobaciones de `diagnose` (UC-01).
3. El sistema recoge:
   - las versiones del programa, de yt-dlp, de yt-dlp-ejs, de deno, de ffmpeg y de Windows;
   - la configuración efectiva;
   - el número de jobs por estado;
   - los últimos fallos con su motivo y su mensaje;
   - el final del log.
4. El sistema limpia los datos sensibles de todo el contenido (SUP-SEC01).
5. El sistema escribe el `.zip` y muestra su ruta.

## Flujos alternativos

- **A1. La base de datos no se puede abrir:** el informe lo registra con la causa y sigue con lo demás.
- **A2. No hay log:** el informe lo indica.

## Excepciones

- **E1. No se puede escribir en la carpeta de estado:** se informa con la carpeta y la causa; código `1`.

## Garantías

- **De éxito:** un archivo con todo lo anterior.
- **Mínima:** el informe nunca contiene credenciales, cookies, contraseñas de un proxy ni archivos multimedia, y nunca modifica la cola.

## Reglas, requisitos y restricciones asociados

- **Requisitos suplementarios:** SUP-SEC01, SUP-SEC02 y SUP-U01.
- **Dependencias:** UC-01; VUC-07 lo reutiliza.

## Criterios de aceptación

1. El informe incluye cada elemento del paso 3, o indica que falta.
2. Ningún valor de una credencial configurada aparece en el informe (se comprueba con valores trampa).
3. Generarlo no cambia la base de datos.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Contenido del informe y limpieza de datos sensibles con valores trampa | Cualquier sistema |
| Base de datos inutilizable (A1) | Cualquier sistema |
