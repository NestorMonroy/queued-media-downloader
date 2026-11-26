# UC-30: Gestionar suscripciones a fuentes de contenido

- **Objetivo:** el User registra fuentes de contenido que le interesan (un canal, una playlist o un feed) con las preferencias con que quiere obtener lo que publiquen, y las consulta, modifica, desactiva, elimina, importa y exporta.
- **Actor principal:** User
- **Disparador:** el User quiere seguir una fuente sin tener que copiar cada URL nueva.
- **Prioridad:** media.
- **Significativo para la arquitectura:** sí: introduce la fuente de contenido y su conjunto de contenido conocido en el modelo de información.
- **Estado:** candidato (propuesta de la instrucción 2.5.0, pendiente de aprobación del Responsable). Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** NewPipe (`SubscriptionEntity`, `FeedGroupEntity`, importar y exportar suscripciones), GreenTuber (`SubsFragment`), YTDLnis (`ObserveSourcesItem`) y VidBee (suscripciones RSS con directorio y plantilla por suscripción); evidencia y nivel en el [análisis de requisitos, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
- **Independencia:** UC-04 expande una playlist una vez; UC-18 guarda preferencias de descarga; UC-21 programa la ejecución de jobs existentes. Ninguno conserva una fuente ni lo que ya se conoce de ella. La suscripción es local: no requiere una cuenta en el servicio ni lo modifica.

## Breve descripción

Una suscripción guarda la URL de la fuente, un nombre, un perfil de descarga (UC-18), un destino opcional, filtros opcionales (palabras clave, tipo de contenido), la política de obtención (revisar o encolar automáticamente) y el conjunto de contenido conocido. Registrar una suscripción no descarga nada ([BR-50](../business-rules.md)); obtener lo nuevo es UC-31.

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User indica la URL de la fuente y, opcionalmente, nombre, perfil, destino, filtros y política.
2. El sistema comprueba que la URL corresponde a una fuente que yt-dlp puede listar (canal, playlist o feed), sin descargar contenido.
3. El sistema registra la suscripción y, si el User lo pidió, marca como conocido el contenido actual de la fuente sin encolarlo (solo lo nuevo a partir de ahora).
4. El sistema informa de la suscripción creada.

## Flujos alternativos

- **A1. Consultar** `[estado: ausente]` (paso 1): el User lista sus suscripciones con su estado (activa o desactivada), su última consulta y su resultado.
- **A2. Modificar** `[estado: ausente]` (paso 1): cambia nombre, perfil, destino, filtros o política; el contenido conocido se conserva.
- **A3. Desactivar y reactivar** `[estado: ausente]` (paso 1): una suscripción desactivada no se consulta en UC-31 y conserva su configuración.
- **A4. Eliminar** `[estado: ausente]` (paso 1): se borra la suscripción y su contenido conocido; los jobs y los resultados que produjo no cambian.
- **A5. Importar** `[estado: ausente]` (paso 1): desde un documento del producto o desde una exportación de suscripciones de un servicio en un formato documentado (por ejemplo, OPML o un JSON de suscripciones); las duplicadas se informan y no se repiten.
- **A6. Exportar** `[estado: ausente]` (paso 1): a un documento versionado, sin credenciales.
- **A7. Organizar en grupos** `[estado: ausente]` (paso 1): el User agrupa suscripciones para consultarlas juntas en UC-31.
- **A8. La fuente pide autorización** `[estado: ausente]` (paso 2): se usa un perfil de acceso (UC-19) como en UC-02 A12.

## Excepciones

- **E1. URL que no es una fuente** `[estado: ausente]` (paso 2): la URL es de un solo contenido; el sistema lo informa y propone encolarla (UC-02).
- **E2. Fuente inaccesible** `[estado: ausente]` (paso 2): fallo de red o restricción del sitio; el sistema no registra la suscripción y clasifica la condición como en UC-11.
- **E3. Documento de importación inválido** `[estado: ausente]` (A5): no se importa nada e indica el motivo.

## Postcondiciones

- La suscripción existe con su configuración y su contenido conocido. No se creó ningún job.

## Requisitos especiales

- Las suscripciones forman parte del respaldo (UC-23) y no contienen credenciales en claro.

## Reglas, requisitos y restricciones asociados

- [BR-50](../business-rules.md); UC-18, UC-19, UC-23; D-21 (retención del contenido conocido).

## Criterios de aceptación

1. Registrar una suscripción no crea jobs.
2. Con «solo lo nuevo», el contenido existente queda conocido y no se encola en la primera consulta de UC-31.
3. Eliminar una suscripción no cambia jobs ni resultados.
4. Importar y exportar conservan las suscripciones sin duplicarlas ni incluir credenciales.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Alta, modificación, baja, importación y exportación con fuentes simuladas | Desarrollo |
