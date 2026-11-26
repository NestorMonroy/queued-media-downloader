# ADR-0036: Frontera de los derechos de uso fuera del núcleo

- **Estado:** Propuesta (instrucción 2.6.0). Se acepta cuando el Responsable apruebe UC-41 o decida D-25.
- **Fecha:** 2026-11-26
- **Relación:**
  - aplica [ADR-0032](adr-0032-reusable-engine-and-platform-capabilities.md) (motor reutilizable en todas las plataformas);
  - realiza BR-54;
  - análisis en el [diseño, Parte 3, §18.7](../design/03-target-architecture-and-evolution.md#187-frontera-comercial) y en el [modelo de negocio](../product-management/business-model-and-case.md).

## Contexto

El modelo comercial aprobado tiene un periodo inicial de 15 días en todas las plataformas y, en Android e iOS, un modo con anuncios y otro sin anuncios adquirido; Windows no muestra anuncios. Cada canal ofrece un mecanismo distinto (Google Play Billing, StoreKit, Microsoft Store) y la distribución directa ninguno.

## Decisión

1. Los derechos de uso (periodo inicial, modo sin anuncios, capacidades adquiridas) viven en un componente fuera del núcleo, con un adaptador por canal.
2. `MediaSource`, `WorkerPool`, `JobStore`, las reglas de identidad, la admisión y la recuperación no dependen de bibliotecas de facturación, StoreKit, SDK de anuncios ni servicios de licencias.
3. No hay servidor de licencias remoto propio.
4. El vencimiento cambia lo que muestra la interfaz; nunca borra, detiene ni altera trabajo.

## Consecuencias

- El núcleo se compila y se prueba sin ningún adaptador comercial.
- Las condiciones pendientes (D-25 a D-27) se resuelven en el componente de derechos y en los adaptadores, sin tocar el motor.

## Alternativas descartadas

- **Comprobaciones comerciales dentro de la admisión de jobs:** acoplaría el motor a cada canal y permitiría que el vencimiento detuviera trabajo.
- **Servidor de licencias propio:** exige cuentas o identificadores de dispositivo y contradice la decisión aprobada.
