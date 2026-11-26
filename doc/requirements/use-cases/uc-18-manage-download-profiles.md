# UC-18: Administrar perfiles de descarga

- **Objetivo:** el User guarda combinaciones de preferencias de descarga con un nombre y las reutiliza al encolar, sin repetir opciones ni conocer la sintaxis de yt-dlp. Las preferencias pueden ser calidad, audio o video, subtítulos, metadatos, miniatura, capítulos, carpeta, plantilla de nombres o límite de ancho de banda.
- **Actor principal:** User
- **Actor secundario:** Programa cliente (encola con un perfil por la línea de comandos)
- **Disparador:** el User descarga a menudo con las mismas preferencias, o quiere cambiar las preferencias por omisión.
- **Relación:** UC-02 lo usa al encolar (A13); UC-20 guarda los perfiles en la configuración.
- **Prioridad:** media
- **Significativo para la arquitectura:** no; las download options ya se fijan por job al encolar
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: ausente. Condición técnica: D-19.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Ampliaciones aceptadas (instrucción 2.6.0):** A8 y A9, propuestas en la 2.5.0; [análisis de requisitos, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
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

- **A1. Consultar:** `[estado: ausente]` `profile list` muestra los nombres y cuál es el predeterminado; `profile show NOMBRE`, su contenido efectivo.
- **A2. Modificar:** `[estado: ausente]` `profile set NOMBRE ...`. Los jobs ya encolados no cambian: conservan la copia que recibieron (BR-33). El sistema informa de cuántos jobs pendientes usaron la versión anterior.
- **A3. Duplicar:** `[estado: ausente]` `profile copy ORIGEN DESTINO`.
- **A4. Eliminar:** `[estado: ausente]` `profile delete NOMBRE`. Los jobs ya encolados no cambian. Si es el predeterminado, se pide confirmación y se vuelve a los valores de la configuración.
- **A5. Predeterminado:** `[estado: ausente]` `profile default NOMBRE`. `enqueue` sin `--profile` lo usa.
- **A6. Opciones explícitas sobre un perfil:** `[estado: ausente]` en `enqueue --profile NOMBRE --format SELECTOR`, la opción explícita prevalece sobre la del perfil, con la misma precedencia que la configuración (SUP-F03).
- **A7. Exportar e importar perfiles:** `[estado: ausente]` dentro de la configuración (UC-20 A5).
- **A8. Perfil elegido según la URL** `[estado: ausente]` (paso 1): un perfil declara patrones de URL. Al encolar sin perfil explícito se usa el primer perfil cuyo patrón coincide y, si ninguno coincide, el predeterminado; el User ve qué perfil se aplicó. Evidencia: YTDLnis (`CommandTemplate.urlRegex`); [análisis, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
- **A9. Preferencias de idioma** `[estado: ausente]` (paso 2): el perfil indica la pista de audio preferida (la original, un idioma o la predeterminada del sitio) y los idiomas de subtítulos. Son conceptos distintos del idioma de la interfaz y del idioma o el país con que se consulta el sitio ([vocabulario](../../design/00-vocabulary.md)). yt-dlp 2026.11.23 marca las pistas originales, predeterminadas y descriptivas en `language_preference` (código de su extractor de YouTube). Evidencia: NewPipe y GreenTuber (`prefer_original_audio`), YTDLnis (`audio_language`) y NewPipeExtractor (`AudioTrackType`).
- **A10. Perfil de procesamiento** `[estado: ausente; propuesto]` (paso 2): un perfil guarda también preferencias de procesamiento (idioma de destino, modelo por operación, voz, formato de subtítulos, nivel de detalle de un resumen) que se fijan al crear el job como cualquier otra preferencia (D-19). Evidencia: preferencias de rendimiento y preajustes compartidos de VoiceStudio (`performance_profiles.py`, `performance_selection.py`); [análisis, §17.4](../requirements-analysis.md#174-proyectos-voces-regeneración-y-perfiles). Propuesta de la instrucción 2.7.0, pendiente de aprobación.

## Excepciones

- **E1. Combinación incompatible** `[estado: ausente]` (por ejemplo, solo audio con subtítulos incrustados, o recodificar sin un codificador disponible, D-18): el sistema nombra las opciones en conflicto y no guarda nada; código `2`.
- **E2. Perfil inexistente:** `[estado: ausente]` código `2`.
- **E3. Perfil que referencia un perfil de acceso inexistente o deshabilitado** `[estado: ausente]` (UC-19): se guarda con un aviso; `enqueue` falla con código `2` mientras no exista.

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
