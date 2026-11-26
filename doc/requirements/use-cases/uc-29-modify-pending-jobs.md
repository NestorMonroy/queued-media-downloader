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
4. El sistema recalcula la identidad de la petición de cada job cuya especificación del resultado cambió y comprueba duplicados con los demás jobs.
5. El sistema registra los cambios con un suceso por job, conserva el identificador, el orden y la procedencia, e informa del resultado por job.

## Flujos alternativos

- **A1. Cambiar solo atributos que no forman parte de la identidad** `[estado: ausente]` (paso 4): destino, hora de inicio o retención. La identidad no cambia y no se repite la comprobación de duplicados.
- **A2. Cambiar el destino** `[estado: ausente]` (paso 3): el nuevo destino se valida como en UC-17 (existe, admite escritura, espacio estimado). Si el job ya tiene una reclamación de outputs, se aplica A5.
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

## Requisitos especiales

- La interfaz de línea de comandos y las interfaces futuras usan el mismo comando público del motor (ADR-0032).

## Reglas, requisitos y restricciones asociados

- [BR-46](../business-rules.md) (prioridad y elegibilidad), [BR-47](../business-rules.md) (modificación de jobs pendientes).
- ADR-0033 (identidad de la petición y de los outputs); D-16.

## Criterios de aceptación

1. Cambiar la calidad de un job pendiente conserva su identificador y su posición, y recalcula su identidad.
2. Un cambio que produce un duplicado no modifica el job.
3. Un job que empezó no se modifica.
4. Una selección mixta informa por job sin revertir los cambios aplicados.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Cambio de calidad, destino y retención en jobs pendientes | Desarrollo |
| Cambio concurrente con el envío de `run` | Desarrollo |
