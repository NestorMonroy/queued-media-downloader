# ADR-0036: Separación de las responsabilidades comerciales respecto del núcleo multimedia

- **Estado:** Orientación aceptada (instrucción 2.7.0, §43 y §45); integración, tecnologías e implementación pendientes. Propuesta en la 2.6.0.
- **Fecha:** 2026-11-26 (reconciliado en la instrucción 2.7.0).
- **Relación:**
  - aplica [ADR-0032](adr-0032-reusable-engine-and-platform-capabilities.md) (motor reutilizable en todas las plataformas);
  - realiza BR-54;
  - análisis en el [diseño, Parte 3, §18.7](../design/03-target-architecture-and-evolution.md#187-frontera-comercial) y en el [modelo de negocio](../product-management/business-model-and-case.md).

## Contexto

El modelo comercial aprobado tiene un periodo inicial de 15 días en todas las plataformas y, en Android e iOS, una modalidad con publicidad y otra sin publicidad adquirida; Windows no muestra publicidad. Cada canal ofrece un mecanismo distinto y la distribución directa ninguno.

## Decisión

**Decisión arquitectónica fundamental (aceptada):** las responsabilidades comerciales (periodo inicial, modalidad, derecho de uso, disponibilidad comercial de una capacidad) se separan del núcleo multimedia. `JobStore`, `MediaSource`, `WorkerPool`, la coordinación, la identidad, los outputs, la recuperación y el procesamiento no dependen de proveedores de pago, publicidad ni tiendas.

**Contratos que deben permanecer estables:**
- un **contrato de acceso** único, que usan todas las interfaces y los consumidores programáticos autorizados, para que ninguna interprete de forma distinta las condiciones aprobadas;
- una **entrada de elegibilidad** en la admisión, por la que el acceso puede condicionar qué jobs son elegibles, sin ser una transición de la máquina de estados de los jobs.

**Alternativas de integración (no seleccionadas):** adaptadores por canal (Google Play Billing, StoreKit, Microsoft Store); en distribución directa, medición local u otra forma pendiente de D-25 y D-27. No se seleccionan servidores de licencias, cuentas ni identificadores persistentes de dispositivo sin una decisión comercial y técnica sustentada.

**Decisiones comerciales pendientes:** D-25 a D-28.

**Tecnologías no seleccionadas:** bibliotecas de facturación, SDK de publicidad y cualquier mecanismo de licencias.

**Implementación futura:** no autorizada; este ADR no especifica un sistema DRM, de identificación de dispositivos ni de licencias remotas.

## Consecuencias

- El núcleo se compila y se prueba sin ningún adaptador comercial.
- U7 deja abierta la elegibilidad a una condición de acceso, sin implementarla (plan de E3, §12.3).

## Alternativas descartadas

- **Comprobaciones comerciales dentro de cada componente multimedia:** acoplaría el motor a cada canal y dejaría que el estado comercial alterase el estado persistido.
- **Que cada interfaz evalúe el acceso por su cuenta:** daría interpretaciones distintas de las mismas condiciones.
