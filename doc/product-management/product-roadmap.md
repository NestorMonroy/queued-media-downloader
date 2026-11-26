# Hoja de ruta del producto

- **Versión:** 2.0 (instrucción 2.7.0, 2026-11-26). 1.0 (instrucción 2.6.0).
- **Responsabilidad:** Gestión del producto (decide el Responsable del proyecto).
- **Estado:** orientación aprobada; **sin fechas**. Los horizontes ordenan por valor y dependencia; no son compromisos de calendario. El alcance de la primera entrega de §4 es una **propuesta**.

## 1. Qué es y qué no es

| Concepto | Qué es | Dónde |
|---|---|---|
| Hoja de ruta del producto | Capacidades previstas, sus condiciones y sus horizontes | Este documento |
| Entrega (*release*) | Conjunto de capacidades que se publica | §4 |
| Iteración | Trabajo autorizado y delimitado por alcance | [Plan de E3](../project-management/iteration-plan-e3.md) |
| EDT, paquete de trabajo, actividad, entregable | Descomposición del trabajo ejecutable | [Plan de E3, §12](../project-management/iteration-plan-e3.md#12-edt-y-líneas-base) |

La hoja de ruta **no** es una unidad de trabajo: un flujo «Futuro» del plan apunta a un horizonte de aquí y no cuenta como planificado.

## 2. Alcance del producto

| Conjunto | Contenido |
|---|---|
| Casos de uso aceptados | 38: UC-01 a UC-11 y UC-14 a UC-40 ([modelo de casos de uso](../requirements/use-case-model.md)) |
| Ampliaciones aprobadas | Las de la 2.5.0 aceptadas en la 2.6.0 (UC-02, UC-05, UC-10, UC-14, UC-18 a UC-21, UC-25) |
| Decisiones comerciales aprobadas | [Modelo de negocio, §3](business-model-and-case.md#3-modelo-comercial-aprobado) |
| Pendiente de reconciliación | UC-41 (candidato) |
| Candidatos nuevos | UC-42, UC-43 |
| Propuestas pendientes de aprobación | Flujos alternativos y de excepción de UC-33 a UC-40; UC-18 A10; SUP-P10 |
| Capacidades condicionadas | UC-19 (perfiles de acceso, condicionado); plataformas móviles (viabilidad por cualificar) |

## 3. Horizontes

| Horizonte | Contenido | Estado | Depende de |
|---|---|---|---|
| H1. Motor y CLI de Windows | Unidades U1 a U16 de E3 | E3 planificada; ejecución no autorizada | Autorización de E3 |
| H2. GUI de Windows | Mismos contratos públicos que la CLI (ADR-0032) | Futuro | H1 |
| H3. Android | Chaquopy como alternativa prioritaria (diseño, §18.9); SUP-C12, SUP-C13 | Futuro; viabilidad por cualificar | H1; D-27 |
| H4. iOS | Integración por cualificar (diseño, §18.9) | Futuro; viabilidad por cualificar | H1; D-27 |
| H5. Procesamiento, primer grupo | UC-33 (transcribir), UC-36 (subtítulos), UC-39 (modelos); UC-18 A10; SUP-P10 | Futuro (objetivos aceptados) | H1; contratos de §5 |
| H6. Procesamiento, segundo grupo | UC-34 (traducir), UC-35 (resumir), UC-37 (voz), UC-38 (doblar); candidatos UC-42 y UC-43 | Futuro | H5; D-28 |
| H7. Organización | UC-40 (colecciones) | Futuro | H1 |
| H8. Reproducción integrada | Objetivo por cualificar: vista previa, reproducción en el producto, segundo plano, imagen en imagen, historial de reproducción. Abrir con otra aplicación ya está aceptado (UC-25 A7). Sin reproductor ni framework elegido | Por cualificar | H2, H3 o H4 |
| H9. Acceso comercial | UC-41 (candidato); periodo inicial en todas las plataformas | Futuro | D-25 a D-27 |

## 4. Alcance propuesto de la primera entrega de Windows

Propuesta de Gestión del producto; **no aprobada**.

| Categoría | Contenido | Recomendación |
|---|---|---|
| Comprometido antes | U1 a U12 de E3 | Incluir |
| Necesario para una entrega utilizable | U13 a U16 (modificación, prioridades, suscripciones, integración, privacidad, actualización) | Incluir |
| Contratos arquitectónicos imprescindibles | Identidad portable y local, varios outputs, resultados derivados en la identidad (U3), contratos públicos (U4), dimensiones de recursos (U8), representación de URLs | Incluir en E3 aunque el procesamiento venga después |
| IA que podría incorporarse | H5: UC-33, UC-36 y UC-39, con inferencia local | **Opcional:** en una iteración posterior a E3 dentro de la misma entrega, si el Responsable quiere una primera entrega con IA. Impacto: añade una iteración, la cualificación de un motor local en Windows x64 y la descarga de modelos; no cambia E3 si sus contratos ya están |
| IA posterior | H6 | Fuera de la primera entrega |
| Comercial | Periodo inicial de 15 días en Windows | Requiere D-25 y D-27 antes de publicar; no bloquea E3 |
| Futuro | H2 a H4, H7 a H9 | Fuera de la primera entrega |

**Razón:** la transcripción, los subtítulos y los modelos son la base de las demás operaciones de procesamiento y tienen evidencia de ejecución local; incluirlos o no se decide al cerrar E3, sin rehacer E3.

## 5. Contratos que el procesamiento necesita de E3

Identidad portable y local (BR-32), varios outputs por job (D-15), identidad de resultados derivados (BR-55), contratos públicos (U4) y dimensiones de recursos (U8). El [plan de E3, §12.3](../project-management/iteration-plan-e3.md#123-contratos-necesarios-antes-de-implementar) dice cuáles deben estar definidos antes de cada unidad.

## 6. Líneas base del producto

| Línea base | Dónde |
|---|---|
| Alcance del producto | §2 |
| Candidatos | Modelo de casos de uso, §4.3 |
| Alcance de entrega propuesto | §4 |
| Hoja de ruta posterior | §3 |
| Decisiones pendientes | [Registro de decisiones](../project-management/governance.md#8-registro-de-decisiones) |
