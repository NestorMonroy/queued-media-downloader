# UC-31: Obtener contenido nuevo de las fuentes

- **Objetivo:** el User sabe qué publicaron sus fuentes desde la última consulta y encola lo que le interesa, o deja que se encole automáticamente según la política de cada suscripción, sin duplicados.
- **Actor principal:** User; el reloj del sistema cuando la consulta está programada.
- **Disparador:** el User pide consultar sus suscripciones, o llega la hora de una consulta programada.
- **Prioridad:** media.
- **Significativo para la arquitectura:** sí: crea jobs desde un proceso no interactivo con procedencia propia y comparte la admisión con la cola.
- **Estado:** aceptado (Responsable, instrucción 2.6.0; propuesto en la 2.5.0). Implementación: ausente. La aceptación no autoriza implementar.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** NewPipe (`NotificationWorker` con intervalo y red configurables que avisa de contenido nuevo de los canales elegidos), GreenTuber (`VideoNotifWorker`), YTDLnis (`ObserveSourceWorker`: solo lo nuevo, reintentar lo que falta, enlaces ignorados y procesados, fin tras N ejecuciones) y VidBee (descarga automática o revisión manual, filtros por palabras clave, solo el último); evidencia y nivel en el [análisis de requisitos, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
- **Independencia:** UC-21 programa cuándo se ejecutan jobs que ya existen; aquí se descubre contenido que todavía no es un job y se decide si se crea. UC-15 inspecciona una URL que el User ya tiene.

## Breve descripción

Para cada suscripción activa (UC-30), el sistema lista la fuente, compara con su contenido conocido, aplica los filtros y presenta lo nuevo. Con la política de revisión, el User selecciona qué encolar; con la de encolado automático, se crean los jobs con el perfil de la suscripción y la procedencia «suscripción» ([BR-46](../business-rules.md), [BR-50](../business-rules.md)).

## Precondiciones

- UC-01 completado; al menos una suscripción activa (UC-30).

## Flujo básico

1. El User pide consultar todas sus suscripciones, un grupo o una.
2. El sistema lista cada fuente con yt-dlp sin descargar contenido.
3. El sistema calcula el contenido nuevo: lo que no está en el conjunto conocido y supera los filtros.
4. El sistema presenta el contenido nuevo por suscripción.
5. El User selecciona qué encolar; el sistema crea los jobs como en UC-02, con el perfil y el destino de la suscripción y la procedencia «suscripción».
6. El sistema añade al conjunto conocido lo presentado (encolado o descartado) y registra la consulta.

## Flujos alternativos

- **A1. Encolado automático** `[estado: ausente]` (paso 4): la suscripción tiene esa política; los jobs se crean sin selección y el sistema avisa (UC-28).
- **A2. Consulta programada** `[estado: ausente]` (paso 1): se ejecuta a la hora configurada con las mismas condiciones de red que UC-21 (conexión medida). Una consulta que coincide con otra en curso no se duplica.
- **A3. Solo el más reciente** `[estado: ausente]` (paso 3): la suscripción limita lo nuevo a los N elementos más recientes; el resto queda conocido.
- **A4. Contenido ya descargado** `[estado: ausente]` (paso 5): coincide con un job o un resultado existente; se marca conocido y no se encola (duplicado como en UC-02).
- **A5. Fuente parcialmente disponible** `[estado: ausente]` (paso 2): la lista se interrumpe; se presenta lo obtenido, el resto no se marca conocido y la consulta queda incompleta.
- **A6. Descartar o ignorar** `[estado: ausente]` (paso 5): el contenido descartado queda conocido y no vuelve a presentarse.
- **A7. Aviso sin encolar** `[estado: ausente]` (paso 4): la suscripción solo avisa de lo nuevo (UC-28).

## Excepciones

- **E1. Fuente inaccesible** `[estado: ausente]` (paso 2): la consulta de esa suscripción falla con la condición clasificada (UC-11); las demás continúan.
- **E2. La fuente ya no existe** `[estado: ausente]` (paso 2): la suscripción queda marcada para revisión, sin borrarse.

## Postcondiciones

- El conjunto conocido de cada suscripción consultada incluye lo presentado; los jobs creados tienen la procedencia «suscripción».
- Ningún resultado existente se borra, aunque haya desaparecido de la fuente.

## Requisitos especiales

- La consulta no descarga contenido y respeta las esperas del sitio (BR-41).

## Reglas, requisitos y restricciones asociados

- [BR-46](../business-rules.md), [BR-50](../business-rules.md); UC-11, UC-21, UC-28; ADR-0031.

## Criterios de aceptación

1. Una segunda consulta sin publicaciones nuevas no presenta nada.
2. El encolado automático crea jobs con la procedencia «suscripción» y sin duplicados.
3. Una fuente que falla no impide consultar las demás.
4. Ningún resultado se borra porque haya desaparecido de la fuente.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Consultas sucesivas con una fuente simulada que publica, retira y falla | Desarrollo |
