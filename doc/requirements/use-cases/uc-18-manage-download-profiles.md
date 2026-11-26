# UC-18: Administrar perfiles de descarga

- **Objetivo:** el User guarda combinaciones de preferencias de descarga con un nombre y las reutiliza al encolar, sin repetir opciones ni conocer la sintaxis de yt-dlp. Las preferencias pueden ser calidad, audio o video, subtítulos, metadatos, miniatura, capítulos, carpeta, plantilla de nombres o límite de ancho de banda.
- **Actor principal:** User
- **Actor secundario:** Programa cliente (encola con un perfil por la línea de comandos)
- **Disparador:** el User descarga a menudo con las mismas preferencias, o quiere cambiar las preferencias por omisión.
- **Relación:** UC-02 lo usa al encolar (A13); UC-20 guarda los perfiles en la configuración.
- **Prioridad:** media
- **Significativo para la arquitectura:** no; las download options ya se fijan por job al encolar
- **Estado:** propuesto; no implementado. Decisión D-19 pendiente.
- **Origen:**
  - **Seal:** preferencias globales y por descarga; plantillas de comandos, con la necesidad de reutilizar sin ejecutar comandos arbitrarios.
  - **Kannagi:** preajustes con `--config-location`.
  - **YTDownload-2026:** valores globales con sustitución por job.
  - **yt-dlp:** archivos de configuración y alias.
  - **Revisión de exclusiones** ([análisis, §12](../requirements-analysis.md#12-reconciliación-de-exclusiones)): la exclusión de los comandos personalizados excluía una solución (ejecutar comandos), no la necesidad (reutilizar preferencias).

## Breve descripción

Un perfil es un conjunto con nombre de download options válidas, guardado en la configuración. `profile` permite crear, consultar, modificar, duplicar, eliminar y marcar uno como predeterminado. Un perfil nunca contiene comandos, scripts ni opciones de yt-dlp sin validar, y nunca contiene credenciales: un perfil de acceso (UC-19) se referencia por su nombre.

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User ejecuta `profile create NOMBRE` con las opciones del perfil (las mismas de `enqueue`).
2. El sistema valida cada opción y su combinación ([BR-33](../business-rules.md)).
3. El sistema guarda el perfil en la configuración y muestra su contenido efectivo.
4. Después, el User encola con `enqueue URL --profile NOMBRE` (UC-02 A13). El job recibe una copia de las opciones del perfil ([BR-33](../business-rules.md)).

## Flujos alternativos

- **A1. Consultar:** `profile list` muestra los nombres y cuál es el predeterminado; `profile show NOMBRE`, su contenido efectivo.
- **A2. Modificar:** `profile set NOMBRE ...`. Los jobs ya encolados no cambian: conservan la copia que recibieron (BR-33). El sistema informa de cuántos jobs pendientes usaron la versión anterior.
- **A3. Duplicar:** `profile copy ORIGEN DESTINO`.
- **A4. Eliminar:** `profile delete NOMBRE`. Los jobs ya encolados no cambian. Si es el predeterminado, se pide confirmación y se vuelve a los valores de la configuración.
- **A5. Predeterminado:** `profile default NOMBRE`. `enqueue` sin `--profile` lo usa.
- **A6. Opciones explícitas sobre un perfil:** en `enqueue --profile NOMBRE --format SELECTOR`, la opción explícita prevalece sobre la del perfil, con la misma precedencia que la configuración (SUP-F03).
- **A7. Exportar e importar perfiles:** dentro de la configuración (UC-20 A5).

## Excepciones

- **E1. Combinación incompatible** (por ejemplo, solo audio con subtítulos incrustados, o recodificar sin un codificador disponible, D-18): el sistema nombra las opciones en conflicto y no guarda nada; código `2`.
- **E2. Perfil inexistente:** código `2`.
- **E3. Perfil que referencia un perfil de acceso inexistente o deshabilitado** (UC-19): se guarda con un aviso; `enqueue` falla con código `2` mientras no exista.

## Garantías

- **De éxito:** el perfil queda guardado y validado.
- **Mínima:** cambiar o eliminar un perfil nunca cambia las opciones de un job ya encolado, ni su recuperación (UC-06).

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-32 (identidad de las variantes) y BR-33.
- **Requisitos suplementarios:** SUP-F03 y SUP-SEC01.
- **Restricciones:** sin ejecución de comandos ni opciones de yt-dlp sin validar.
- **Dependencias:** UC-02 y UC-20; UC-19 si el perfil usa un perfil de acceso.

## Criterios de aceptación

1. Un job encolado con un perfil se descarga con las opciones que tenía el perfil al encolar, aunque después se modifique o elimine.
2. Una combinación incompatible nunca se guarda.
3. Un perfil nunca contiene credenciales ni comandos.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Ciclo de vida completo, validación y precedencia | Cualquier sistema |
| Modificar un perfil con jobs pendientes y recuperar tras un cierre | Cualquier sistema |
