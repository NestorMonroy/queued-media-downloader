# UC-26: Verificar los resultados descargados

- **Objetivo:** el User comprueba, sin volver a descargar, que los resultados de sus jobs existen, son suyos, son legibles y corresponden a lo que pidió: streams esperados, duración y archivos complementarios.
- **Actor principal:** User
- **Disparador:** el User duda de un archivo (un reproductor falla, el equipo se apagó) o quiere comprobar una carpeta antes de borrar originales o moverla.
- **Relación:** comparte el mecanismo con la verificación al completar (UC-03, BR-30) y en la recuperación (UC-06 A11, BR-23). UC-25 usa su resultado antes de borrar. La validación de la campaña usa el mismo mecanismo y no lo duplica.
- **Prioridad:** media
- **Significativo para la arquitectura:** no; reutiliza ffprobe, ya incluido
- **Estado:** propuesto; no implementado. Depende de D-9 y D-15.
- **Origen:**
  - **FFmpeg:** ffprobe (streams, duración, contenedor).
  - **Producto:** la propiedad por reclamaciones; la evidencia de T42 (cola 5.7-r2) y R-25.
  - **Revisión de exclusiones:** ninguna referencia verifica tras descargar, pero eso no prueba que la necesidad no exista.

## Breve descripción

`verify [ID...]` comprueba cada resultado registrado sin peticiones al sitio:
- existencia y tamaño;
- propiedad: reclamación y owner token;
- legibilidad con ffprobe;
- streams esperados según la petición: audio y video, o solo audio;
- duración frente a la guardada al descargar;
- presencia de los complementarios obligatorios.

El método depende del tipo de resultado: un subtítulo o un `info.json` se comprueban por su formato, no con ffprobe.

## Precondiciones

- UC-01 completado (ffprobe verificado).

## Flujo básico

1. El User ejecuta `verify ID`.
2. El sistema obtiene los resultados registrados del job y lo que se pidió.
3. Para cada resultado, aplica las comprobaciones de su tipo ([BR-38](../business-rules.md)).
4. El sistema informa por resultado: correcto, ausente, ajeno, ilegible o distinto de lo pedido, con el motivo.
5. Termina con código `0` si todo es correcto, o `1` si algo falla. El estado de los jobs no cambia.

## Flujos alternativos

- **A1. Toda la cola o una playlist:** `verify --all` o `verify --parent ID`, con un resumen.
- **A2. Sin duración guardada** (jobs de versiones anteriores): solo existencia, propiedad, legibilidad y streams.
- **A3. Resultado opcional ausente:** se informa como aviso, no como fallo (BR-30).
- **A4. Salida para otros programas:** `--json`.

## Excepciones

- **E1. ffprobe ausente o roto:** como UC-01 A5; no se verifica nada; código `2`.
- **E2. Job sin resultados registrados** (expansiones, jobs no completados): se informa.

## Garantías

- **De éxito:** un informe por resultado.
- **Mínima:** verificar nunca modifica archivos, estados ni reclamaciones, ni hace peticiones al sitio.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-23, BR-29, BR-30, BR-31 y BR-38.
- **Requisitos suplementarios:** SUP-R10 y SUP-I01.
- **Restricciones:** no se vuelve a descargar para verificar.
- **Dependencias:** UC-03, UC-06 y UC-25; D-9 y D-15.

## Criterios de aceptación

1. Un archivo truncado, sin el stream de audio o de otra duración se informa como fallo.
2. Un archivo sin reclamación propia se informa como ajeno, aunque tenga el nombre esperado.
3. Verificar no cambia la base de datos ni los archivos.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Archivos correctos, truncados, sin un stream y ajenos, generados con ffmpeg | Cualquier sistema |
| ffprobe incluido | **Windows** |
