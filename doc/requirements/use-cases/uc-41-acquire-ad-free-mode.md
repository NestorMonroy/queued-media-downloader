# UC-41: Adquirir acceso a la aplicación

- **Objetivo:** el User consulta su acceso a la aplicación (periodo inicial, modalidad vigente) y, en las plataformas donde existe, adquiere o restaura la modalidad sin publicidad.
- **Actor principal:** User
- **Disparador:** el User consulta su acceso, termina su periodo inicial o quiere quitar la publicidad.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** sí: el acceso se evalúa con un contrato compartido por todas las interfaces y fuera de los componentes multimedia (ADR-0036).
- **Estado:** candidato (propuesta de la instrucción 2.7.0, pendiente de aprobación del Responsable). Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** Modelo comercial aprobado y ratificado (instrucciones 2.6.0 y 2.7.0, [modelo de negocio, §3](../../product-management/business-model-and-case.md#3-modelo-comercial-aprobado)); mecanismos documentados de Google Play y App Store (§6 del mismo documento). Reconciliado en la instrucción 2.7.0: el objetivo anterior («Adquirir el modo sin anuncios») no tenía sentido en Windows.
- **Independencia:** El periodo inicial empieza por un comportamiento del sistema (evento pendiente en D-25), no por una petición del User. El modo privado (UC-20 A8) no cambia la publicidad y la modalidad comercial no cambia qué datos se guardan.

## Breve descripción

El User consulta su acceso: días restantes del periodo inicial y modalidad vigente. En Android e iOS, al terminar el periodo inicial puede continuar con publicidad o adquirir la modalidad sin publicidad, y puede restaurar una adquisición. En Windows no hay publicidad; qué ocurre al terminar el periodo inicial está pendiente (D-27). Precio, forma de contratación y capacidades incluidas están pendientes (D-26, D-28).

## Precondiciones

- La aplicación está instalada desde un canal.

## Flujo básico

1. El User pide consultar su acceso.
2. El sistema muestra el estado del periodo inicial y la modalidad vigente.
3. En Android o iOS, el User elige adquirir la modalidad sin publicidad.
4. El adaptador del canal realiza la adquisición con el mecanismo de la tienda.
5. El sistema registra el resultado de la adquisición y la interfaz deja de mostrar publicidad; los jobs, outputs y datos no cambian.

## Flujos alternativos

- **A1. Continuar con publicidad** `[estado: ausente]` (paso 3): en Android o iOS, tras el periodo inicial, el User sigue con la modalidad con publicidad.
- **A2. Restaurar una adquisición** `[estado: ausente]` (paso 3): en una reinstalación o un dispositivo nuevo, el adaptador consulta al canal y registra la adquisición existente.
- **A3. Adquisición pendiente** `[estado: ausente]` (paso 4): el canal informa de una compra pendiente; el sistema lo muestra y no cambia la modalidad hasta que el canal la confirme.
- **A4. Windows al terminar el periodo inicial** `[estado: ausente]` (paso 2): el comportamiento está pendiente de la decisión D-27; no se presupone bloqueo, uso ilimitado ni una forma de pago.

## Excepciones

- **E1. Adquisición cancelada o fallida** `[estado: ausente]` (paso 4): no se registra ninguna adquisición y nada más cambia.
- **E2. Canal no disponible** `[estado: ausente]` (paso 4): el sistema no puede consultar al canal; conserva la última modalidad registrada según D-25 y lo indica.

## Postcondiciones

- La modalidad registrada coincide con la del canal; el trabajo del User no cambió.

## Requisitos especiales

- Ningún componente multimedia depende del mecanismo de adquisición ni de publicidad (BR-54, ADR-0036).

## Reglas, requisitos y restricciones asociados

- [BR-49](../business-rules.md), [BR-54](../business-rules.md); D-25 a D-28; SUP-C12, SUP-C13; R-40, R-41.

## Criterios de aceptación

1. Adquirir, restaurar o perder una adquisición no altera jobs, outputs ni configuración.
2. Todas las interfaces muestran la misma modalidad para el mismo estado registrado.
3. El núcleo se compila y se prueba sin ningún adaptador comercial.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Adaptador de canal simulado: adquisición, pendiente, restauración, fallo y canal no disponible | Desarrollo |
