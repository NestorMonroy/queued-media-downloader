# UC-41: Adquirir el modo sin anuncios

- **Objetivo:** el User de Android o iOS deja de ver anuncios después del periodo inicial adquiriendo el modo sin anuncios, y lo recupera en una reinstalación.
- **Actor principal:** User
- **Disparador:** el User elige quitar los anuncios o restaurar una compra.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** sí: frontera comercial fuera del núcleo ([BR-54](../business-rules.md)); mecanismo distinto por canal.
- **Estado:** candidato (propuesta de la instrucción 2.6.0, pendiente de aprobación del Responsable). Horizonte: futuro. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** Modelo comercial aprobado en la instrucción 2.6.0 ([modelo de negocio, §3](../../product-management/business-model-and-case.md#3-modelo-comercial-aprobado)); mecanismos documentados de Google Play y App Store (§6 del mismo documento). Ninguna referencia de código abierto implementa compras; los APK modificados se excluyen. Evidencia y nivel en el [análisis de requisitos, §16](../requirements-analysis.md#16-descubrimiento-260-ia-privacidad-y-modelo-comercial).
- **Independencia:** No existe en Windows, que no muestra anuncios. El modo privado (UC-20 A8) no quita anuncios y este modo no cambia qué datos se guardan ([BR-49](../business-rules.md)).

## Breve descripción

El User pide el modo sin anuncios; el adaptador del canal realiza la compra con el mecanismo de la tienda; el derecho de uso se registra fuera del núcleo y la interfaz deja de mostrar anuncios. Las condiciones (pago único o recurrente, precio, alcance) están pendientes (D-26).

## Precondiciones

- Plataforma Android o iOS, instalada desde un canal con mecanismo de compra.
- Las decisiones D-25 y D-26 están tomadas.

## Flujo básico

1. El User pide quitar los anuncios.
2. El sistema muestra la oferta del canal con sus condiciones.
3. El User confirma la compra en el mecanismo de la tienda.
4. El adaptador del canal recibe la confirmación y registra el derecho de uso.
5. La interfaz deja de mostrar anuncios; los jobs y resultados no cambian.

## Flujos alternativos

- **A1. Restaurar la compra** `[estado: ausente]` (paso 1): en una reinstalación o un dispositivo nuevo, el adaptador consulta al canal y registra el derecho existente.
- **A2. Sin conexión** `[estado: ausente]` (paso 2): la oferta no está disponible; el último derecho registrado se respeta según D-25.
- **A3. Vencimiento o reembolso** `[estado: ausente]` (paso 5): el derecho deja de ser válido; vuelven los anuncios y nada del trabajo del User se borra, detiene ni altera ([BR-54](../business-rules.md)).

## Excepciones

- **E1. Compra cancelada o fallida** `[estado: ausente]` (paso 3): no se registra ningún derecho y no cambia nada más.

## Postcondiciones

- El derecho de uso registrado coincide con el del canal; el trabajo del User no cambió.

## Requisitos especiales

- Ningún componente del núcleo depende del mecanismo de compra ni de SDK de anuncios.

## Reglas, requisitos y restricciones asociados

- [BR-49](../business-rules.md), [BR-54](../business-rules.md); SUP-C12, SUP-C13; R-40, R-41.

## Criterios de aceptación

1. Comprar o perder el derecho no altera jobs, resultados ni configuración.
2. El núcleo compila y se prueba sin el adaptador del canal.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Adaptador de canal simulado: compra, restauración, reembolso y sin conexión | Desarrollo |
