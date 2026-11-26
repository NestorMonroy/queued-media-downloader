# UC-29: Modificar jobs no terminados

- **Objetivo:** el User cambia lo que pidió para uno o varios jobs que todavía no han terminado (resultado, perfil, destino, hora de inicio o retención) sin cancelarlos y volver a encolarlos, y sin perder su lugar ni su historial.
- **Actor principal:** User
- **Disparador:** el User se da cuenta, después de encolar, de que quiere otra calidad, otro idioma, otro destino u otro perfil.
- **Prioridad:** media. Hoy la alternativa es cancelar (UC-05) y volver a encolar (UC-02), que pierde el orden y crea otro job.
- **Significativo para la arquitectura:** sí: toca la identidad de la petición (D-16, ADR-0033), la detección de duplicados, las reclamaciones de outputs y la admisión.
- **Estado:** aceptado (Responsable, instrucción 2.6.0; propuesto en la 2.5.0). Implementación: ausente. La aceptación no autoriza implementar.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** YTDLnis (cambio de formato de varios jobs en cola con `UpdateMultipleDownloadsFormatsWorker` y `DownloadItemConfigureMultiple`; estados `Saved`, `Scheduled` y `QueuedPaused`; pausar y reanudar un job es UC-14 A7); evidencia y nivel en el [análisis de requisitos, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
- **Independencia:** UC-02 crea jobs, UC-05 los cancela, UC-07 reintenta los fallidos y UC-18 gestiona los perfiles que se aplicarán a jobs futuros. Ninguno cambia la petición de un job existente; hacerlo con cancelar y encolar cambia la identidad del job y pierde el orden, la procedencia y el historial.

## Breve descripción

El User selecciona jobs no terminados y cambia uno o varios atributos de la petición. El sistema valida el cambio igual que al encolar (UC-02), recalcula la identidad de la petición si cambia la especificación del resultado, vuelve a comprobar duplicados y conserva el identificador, el orden y la procedencia del job ([BR-47](../business-rules.md)). Que el job tenga parciales o reclamaciones no impide modificarlo: se comprueba si son compatibles con la nueva petición, y nada incompatible se reutiliza ni se borra en silencio. Un job terminado no se modifica.

## Precondiciones

- UC-01 completado.
- Los jobs no están terminados (pendientes, aplazados, recuperables o, tras detenerlos, activos).

## Flujo básico

1. El User selecciona uno o varios jobs no terminados y los atributos que quiere cambiar.
2. El sistema comprueba el estado de cada job: un job terminado no se modifica (A3) y uno activo exige detenerlo antes (A6).
3. El sistema valida el resultado de aplicar los cambios con las mismas reglas que UC-02 y UC-18 (combinaciones incompatibles, perfil de acceso existente).
4. El sistema clasifica cada cambio con la matriz de modificaciones: recalcula la identidad **portable** si cambia la especificación del resultado o la clase de contexto de acceso, recalcula la identidad **local** si cambia la portable o el destino, y comprueba duplicados con la identidad local ([BR-32](../business-rules.md), [BR-47](../business-rules.md)).
5. El sistema registra los cambios con un suceso por job, conserva el identificador, el orden y la procedencia, e informa del resultado por job.

## Flujos alternativos

- **A1. Cambiar solo atributos que no forman parte de la identidad** `[estado: ausente]` (paso 4): prioridad, orden, hora de inicio o retención. Ninguna identidad cambia y no se repite la comprobación de duplicados; la prioridad y la hora pueden cambiar la elegibilidad (BR-46).
- **A2. Cambiar el destino** `[estado: ausente]` (paso 3): el nuevo destino se valida como en UC-17 (existe, admite escritura, espacio estimado). La identidad portable se conserva y la local se recalcula, así que se vuelve a comprobar el duplicado en el nuevo destino (otra carpeta es una variante, BR-32). Si el job ya tiene parciales o una reclamación de outputs, se aplica A5; un cambio de destino durante la publicación de un output no se aplica hasta que la publicación termina.
- **A3. Varios jobs con resultados distintos** `[estado: ausente]` (paso 5): unos se modifican y otros no (activo, terminado, combinación incompatible, duplicado); cada uno se informa por separado y no se revierten los que se modificaron.
- **A5. Job con parciales o reclamaciones** `[estado: ausente]` (paso 4): el sistema comprueba si los parciales y la reclamación son compatibles con la nueva petición (misma identidad del resultado y mismo destino). Si lo son, se conservan. Si no, muestra qué quedaría incompatible y el User elige apartarlos (se conservan sin reclamación activa) o descartarlos; sin esa elección, el job no se modifica ([BR-47](../business-rules.md)).
- **A6. Job activo** `[estado: ausente]` (paso 2): el sistema ofrece detenerlo de forma recuperable (UC-14) y, una vez detenido, aplica el flujo con la comprobación de A5.
- **A4. El cambio produce un duplicado** `[estado: ausente]` (paso 4): la nueva identidad coincide con la de otro job pendiente o activo. El job no se modifica y el sistema indica con qué job coincide.

## Excepciones

- **E1. El job cambió de estado entre la selección y la aplicación** `[estado: ausente]` (paso 2): si empezó, se trata como A6; si terminó, no se modifica y el sistema lo indica.
- **E2. Job inexistente** `[estado: ausente]` (paso 2): el sistema lo informa y sigue con los demás.

## Postcondiciones

- Cada job modificado conserva su identificador, su orden y su procedencia, y su petición refleja los cambios.
- Ningún job terminado cambió; ningún job activo cambió sin detenerse antes; ningún parcial ni resultado incompatible se reutilizó ni se borró sin la decisión del User.

## Matriz de modificaciones

Qué identidad o evaluación afecta cada cambio. «Portable» es la media key con la especificación del resultado y la clase de contexto de acceso; «local», la portable con el destino normalizado (BR-32, D-16); la identidad del job nunca cambia.

| Modificación | Identidad portable | Identidad local | Evaluación requerida |
|---|---|---|---|
| Prioridad u orden | No | No | Orden de envío (BR-46) |
| Hora de inicio | No | No | Elegibilidad temporal (BR-46) |
| Resolución, formato o contenedor | Sí | Sí | Especificación del resultado; duplicados; compatibilidad de parciales (A5) |
| Idioma de pistas o subtítulos | Sí | Sí | Contenido solicitado; duplicados; compatibilidad de parciales |
| Destino | No | Sí | Duplicados en el destino; propiedad y reclamaciones (A2, A5) |
| Perfil de descarga | Según los atributos que cambie | Según los atributos que cambie | Configuración efectiva: se evalúa cada atributo del perfil por su fila |
| Perfil de acceso | Sí (clase de contexto de acceso) | Sí | Equivalencia de contexto: otro contexto es otro objetivo (diseño, Parte 3, §6.2) |
| Modelo o versión de modelo (operaciones de procesamiento) | Sí | Sí | Especificación de procesamiento y compatibilidad de resultados intermedios ([BR-55](../business-rules.md)) |
| Parámetros de procesamiento | Solo los que afectan al resultado | Igual que la portable | Identidad y reutilización (BR-55) |
| Outputs solicitados | Sí | Sí | Obligaciones de terminación: qué outputs debe publicar el job (D-15) |
| Retención | No | No | Ninguna |

**Por estado del job:** nunca iniciado, pendiente y aplazado admiten cualquier fila; interrumpido o con parciales, con la comprobación de A5; con resultados intermedios, los incompatibles con el cambio quedan invalidados y no se reutilizan (diseño, §18.3); con outputs ya publicados, el cambio no los modifica ni los reemplaza: los outputs nuevos se publican según D-15 y BR-53; activo, solo tras detenerlo (A6); terminado, no se modifica (se crea un job nuevo). La existencia de una reclamación no prohíbe por sí sola modificar.

## Requisitos especiales

- **Concurrencia** (condiciones, sin elegir todavía el mecanismo de bloqueo o transacción): un cambio no se aplica a un job mientras se admite ni a un output mientras se publica; las reclamaciones afectadas se reconcilian en la misma operación que el cambio; la comprobación de duplicados y la aplicación del cambio no pueden intercalarse con otro encolado o modificación que produzca la misma identidad local; la información de recuperación sigue enlazada al job tras el cambio.

- La interfaz de línea de comandos y las interfaces futuras usan el mismo comando público del motor (ADR-0032).

## Reglas, requisitos y restricciones asociados

- [BR-32](../business-rules.md) (identidad portable y local), [BR-46](../business-rules.md) (prioridad y elegibilidad), [BR-47](../business-rules.md) (modificación de jobs no terminados), [BR-55](../business-rules.md) (resultados derivados).
- ADR-0033 (identidad de la petición y de los outputs); D-16.

## Criterios de aceptación

1. Cambiar la calidad de un job pendiente conserva su identificador y su posición, y recalcula su identidad.
2. Un cambio que produce un duplicado no modifica el job.
3. Un job activo solo se modifica después de detenerlo; un job terminado no se modifica.
4. Una selección mixta informa por job sin revertir los cambios aplicados.
5. Cambiar el destino conserva la identidad portable, recalcula la local y detecta un duplicado en el nuevo destino.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Cambio de calidad, destino y retención en jobs pendientes | Desarrollo |
| Cambio concurrente con el envío de `run` | Desarrollo |
