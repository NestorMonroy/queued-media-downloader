# Hoja de ruta del producto

- **Versión:** 1.0 (instrucción 2.6.0, 2026-11-26).
- **Responsabilidad:** Gestión del producto (decide el Responsable del proyecto).
- **Estado:** orientación aprobada; **sin fechas**. Los horizontes son orden de valor y dependencia, no compromisos de calendario. El alcance de publicación de §3 es una **propuesta**.

## 1. Orientación estratégica

El producto evoluciona de administrar obtenciones multimedia a **obtener, organizar y administrar resultados** y, después, **procesar audio, video y texto con IA**: transcripción, traducción, resúmenes, subtítulos, voz y doblaje. Plataformas: Windows CLI, Windows GUI, Android e iOS; Windows x64 y la CLI van primero ([ADR-0032](../notes/adr-0032-reusable-engine-and-platform-capabilities.md)).

La IA no es un caso de uso («usar IA» no es un objetivo del User): cada operación es un objetivo distinto (D-23) con sus propias entradas, resultados y recuperación.

## 2. Horizontes

| Horizonte | Contenido | Estado | Depende de |
|---|---|---|---|
| H1. Motor y CLI de Windows | Alcance aceptado: 30 casos de uso, unidades U1 a U16 de E3 | E3 planificada; ejecución no autorizada | Autorización de E3 |
| H2. GUI de Windows | Mismos comandos y consultas públicas que la CLI (ADR-0032) | Futuro | H1 |
| H3. Android | Chaquopy como alternativa prioritaria (diseño, §18.9); canales y condiciones de Google Play (SUP-C12, SUP-C13) | Futuro; viabilidad por cualificar | H1; D-27 |
| H4. iOS | Ejecución en proceso sin restringirse a hilos como única opción (diseño, §18.9) | Futuro; viabilidad por cualificar | H1; D-27 |
| H5. Procesamiento con IA | Candidatos UC-33 a UC-39 | Futuro (unidad Roadmap) | H1; D-28; cualificación de motores |
| H6. Colecciones | Candidato UC-40 | Futuro (unidad Roadmap) | H1 |
| H7. Modos comerciales | Candidato UC-41 en Android e iOS; periodo inicial en todas las plataformas | Futuro (unidad Roadmap) | H3 o H4; D-25 a D-27 |

Sin candidato en esta instrucción, por falta de evidencia de necesidad propia más allá de las aplicaciones de referencia: reproducción integrada y vista previa dentro del producto. Abrir con otra aplicación ya está aceptado (UC-25 A7). Quedan como objetivos por cualificar.

## 3. Alcance de publicación propuesto

Propuesta de Gestión del producto; no aprobada.

| Publicación | Contenido propuesto | Condición |
|---|---|---|
| Primera publicación de Windows CLI | H1 completo, con la campaña de Windows que corresponda | E3 terminada y evaluada |
| Primera publicación de Windows GUI | H2 sobre el mismo motor | H1 publicado |
| Primera publicación móvil | H3 o H4 con el periodo inicial y los dos modos de §3 del [modelo de negocio](business-model-and-case.md#3-modelo-comercial-aprobado) | D-25 a D-27 |
| Publicaciones con IA | Candidatos de H5 que se acepten | D-28 y cualificación |

## 4. Líneas base del producto

| Línea base | Dónde |
|---|---|
| Alcance del producto (aceptado) | [Visión](../requirements/vision.md) y [modelo de casos de uso](../requirements/use-case-model.md) |
| Candidatos | Modelo de casos de uso, §4.3 |
| Alcance de publicación propuesto | §3 |
| Hoja de ruta posterior | §2, horizontes H2 a H7 |
| Decisiones pendientes | [Registro de decisiones](../project-management/governance.md#8-registro-de-decisiones) |
