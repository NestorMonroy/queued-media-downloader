# Gobierno del proyecto

- **Versión:** 1.0 (instrucción 2.6.0, 2026-11-26).
- **Fecha:** 2026-11-26
- **Revisión:** al cerrar cada iteración y ante cada cambio de línea base.
- **Estado:** vigente. Describe cómo se gobierna el trabajo; no autoriza E3 ni ninguna implementación.

Este documento reúne en un solo lugar los artefactos de dirección de proyectos de PMBOK 8 que el proyecto adapta: modelo de gobierno, autoridades, control de cambios, líneas base, registros (supuestos, incidencias, cambios, lecciones aprendidas), matriz de asignación de responsabilidades y registro de decisiones. La descomposición del trabajo (EDT) y los paquetes de trabajo están en el [plan de E3](iteration-plan-e3.md#12-edt-y-líneas-base), los riesgos en la [lista de riesgos](risk-list.md) y el producto en el [espacio de gestión del producto](../product-management/business-model-and-case.md). No hay procesos paralelos: cada asunto tiene un solo artefacto canónico.

## 1. Fuentes y división de responsabilidades metodológicas

| Marco | Gobierna | Artefactos canónicos |
|---|---|---|
| PMBOK 8 (*The Standard for Project Management* y *PMBOK Guide*, 8.ª ed.) | Gobierno, alcance del proyecto, cronograma, finanzas, interesados y recursos, riesgo y adaptación (*tailoring*) | Este documento, plan de iteración, lista de riesgos, espacio de producto (caso de negocio y finanzas) |
| BABOK v3 | Requisitos: elicitación, análisis, trazabilidad, priorización, aprobación | Visión, modelo de casos de uso, especificaciones, reglas de negocio, especificación suplementaria, análisis de requisitos |
| RUP | Ingeniería: fases, iteraciones, disciplinas de análisis y diseño, implementación y pruebas | Caso de desarrollo, documentos de diseño, ADR, planes de iteración |

PMBOK 8 se usó desde el PDF entregado (386 páginas); se verificaron los siete dominios de desempeño (Gobierno, Alcance, Cronograma, Finanzas, Interesados, Recursos, Riesgo), los procesos de cada dominio, la adaptación (§3), las áreas de enfoque (§4.5) y las consideraciones de gestión del producto (§2.3).

## 2. Roles y autoridades

Los roles son responsabilidades, no personas ni herramientas ([ADR-0023](../notes/adr-0023-roles-and-scope-boxed-iterations.md)). Una persona puede asumir varios.

| Rol | Autoridad | Lo asume hoy |
|---|---|---|
| Gestión del producto | Visión, modelo y caso de negocio, hoja de ruta, decisiones comerciales, estrategia de publicación | Responsable del proyecto |
| Dirección del proyecto | Gobierno, alcance del proyecto, líneas base, control de cambios, riesgos, autorización de iteraciones | Responsable del proyecto |
| Análisis de negocio | Necesidades, interesados, alternativas, decisiones pendientes y su redacción | Agente de implementación (propone); Responsable (aprueba) |
| Requisitos | Casos de uso, reglas y requisitos suplementarios; su estado | Agente (redacta); Responsable (acepta) |
| Análisis y diseño | Realización de casos de uso, vocabulario, contratos | Agente |
| Arquitectura | Decisiones de arquitectura (ADR) | Agente (propone); Responsable (acepta) |
| Cualificación técnica | Experimentos y evidencia L0 a L5 | Agente; Evaluador en Windows para la evidencia de Windows |
| Publicación y distribución | Canales, paquetes, condiciones de cada tienda | Responsable (decide); Agente (analiza) |
| Calidad y aceptación | Criterios de terminado, comprobaciones, aceptación de iteraciones | Responsable (acepta); Agente (ejecuta las comprobaciones locales) |

**Decisiones reservadas al Responsable:** aprobar o retirar casos de uso, reglas y requisitos; aceptar ADR; autorizar una iteración o una implementación; cambiar una línea base; toda decisión comercial (precio, modalidad de pago, anuncios, canales); integrar en `main` cuando la instrucción no delega esa integración. El Agente nunca convierte una propuesta, una hipótesis o una deducción en una restricción.

## 3. Matriz de asignación de responsabilidades (RAM, RACI)

R ejecuta, A aprueba y rinde cuentas, C es consultado, I es informado. «Resp.» es el Responsable del proyecto; «Agente», el Agente de implementación; «Eval.», el Evaluador en Windows.

| Entregable o actividad | Resp. | Agente | Eval. |
|---|---|---|---|
| Visión, hoja de ruta y caso de negocio | A, R | C | I |
| Modelo comercial y condiciones pendientes | A, R | C | — |
| Casos de uso, reglas, requisitos suplementarios | A | R | I |
| Análisis de requisitos y decisiones pendientes | A | R | — |
| Diseño, vocabulario, contratos | C | R | — |
| ADR | A | R | — |
| Experimentos y evidencia en Linux | I | R | — |
| Evidencia en Windows (T42 y siguientes) | A | C | R |
| Plan de iteración, EDT y líneas base | A | R | I |
| Lista de riesgos y registros de este documento | A | R | C |
| Comprobaciones locales (`scripts/run_checks.py`) | I | R | — |
| Integración en `main` | A | R cuando se delega | — |
| Autorización de E3 | A, R | — | I |

## 4. Procesos de PMBOK 8 y su adaptación

La columna «Adaptación» dice cómo se aplica cada proceso en un proyecto de una persona con un agente, iteraciones delimitadas por alcance y sin presupuesto monetario aprobado. Un proceso marcado «No aplica» queda omitido por esa razón, no olvidado.

### 4.1 Gobierno

| Proceso | Adaptación |
|---|---|
| Initiate Project or Phase | Cada instrucción numerada del Responsable inicia una fase de trabajo; cada iteración se inicia con su plan aprobado |
| Integrate and Align Project Plans | El plan de iteración, este documento, la lista de riesgos y el espacio de producto se referencian entre sí; `check_requirements_model.py` verifica la coherencia documental |
| Plan Sourcing Strategy | Adquisición de software de terceros: dependencias fijadas (`uv.lock`, `vendor/`); no se cambian sin autorización (D-8) |
| Manage Project Execution | Una rama por tarea, comprobaciones locales, integración `--ff-only` |
| Manage Quality Assurance | Seis comprobaciones (formato, estilo, tipos, arquitectura, requisitos, pruebas); TDD ([ADR-0024](../notes/adr-0024-verification-by-tdd-and-review-focus.md)) |
| Manage Project Knowledge | Documentos canónicos en `doc/`, ADR y registro de lecciones (§7.4) |
| Monitor and Control Project Performance | Avance en tareas terminadas sobre el total de la iteración, no en días (caso de desarrollo, §5) |
| Assess and Implement Changes | Control de cambios (§5) |
| Close Project or Phase | Evaluación de la iteración con sus criterios; campaña de Windows cuando corresponde |

### 4.2 Alcance

| Proceso | Adaptación |
|---|---|
| Plan Scope Management | Este documento (§5, §6) y el caso de desarrollo |
| Elicit and Analyze Requirements | Disciplina de requisitos con técnicas de BABOK v3; el análisis de requisitos es el registro |
| Define Scope | Visión (alcance del producto) y plan de iteración (alcance del proyecto) |
| Develop Scope Structure | EDT por unidades U1 a U16 y Roadmap en el [plan de E3, §12](iteration-plan-e3.md#12-edt-y-líneas-base) |
| Monitor and Control Scope | Tablas de cobertura verificadas automáticamente: cada flujo pendiente tiene una sola unidad y un alcance |
| Validate Scope | Aceptación de la iteración por el Responsable con los criterios del plan |

### 4.3 Cronograma

| Proceso | Adaptación |
|---|---|
| Plan Schedule Management | Iteraciones delimitadas por alcance, sin fechas comprometidas ([ADR-0023](../notes/adr-0023-roles-and-scope-boxed-iterations.md)) |
| Develop Schedule | Orden por dependencias entre unidades (grafo sin ciclos, verificado); la hoja de ruta del producto no tiene fechas |
| Monitor and Control Schedule | Tareas terminadas sobre el total; las esperas conocidas son decisiones del Responsable y evaluaciones en Windows |

### 4.4 Finanzas

| Proceso | Adaptación |
|---|---|
| Plan Financial Management | Variables financieras del producto en el [caso de negocio](../product-management/business-model-and-case.md#5-variables-financieras) |
| Estimate Costs | Solo variables y fuentes de coste (canales, firma de código, inferencia remota); ningún importe inventado |
| Develop Budget | No aplica: no hay presupuesto aprobado |
| Monitor and Control Finances | No aplica hasta que exista presupuesto |

### 4.5 Interesados

| Proceso | Adaptación |
|---|---|
| Identify Stakeholders | Visión, §3; los canales de distribución se tratan como interesados con condiciones propias |
| Plan Stakeholder Engagement | Instrucciones numeradas del Responsable e informes finales |
| Plan Communications Management | Comunicación por instrucciones, informes y *commits*; documentos en español, identificadores en inglés |
| Manage Stakeholder Engagement | Preguntas al Responsable solo para decisiones que le pertenecen |
| Manage Communications | Informe final de cada instrucción con respuestas explícitas |
| Monitor Stakeholder Engagement | Las correcciones del Responsable se registran como lecciones (§7.4) |
| Monitor Communications | Idem |

### 4.6 Recursos

| Proceso | Adaptación |
|---|---|
| Plan Resource Management | Roles de §2; entornos: Linux para el Agente, Windows para el Evaluador |
| Estimate Resources | Recursos técnicos de la cualificación (memoria, disco, GPU) en los experimentos, no recursos humanos |
| Acquire Resources | Herramientas de investigación en entornos virtuales aislados; ningún modelo grande descargado |
| Lead the Team | Instrucciones y reglas permanentes del Responsable |
| Monitor and Control Resourcing | Disponibilidad del Evaluador en Windows como condición de cierre |

### 4.7 Riesgo

| Proceso | Adaptación |
|---|---|
| Plan Risk Management | Lista de riesgos con exposición = probabilidad × impacto |
| Identify Risks | Cada instrucción revisa y añade riesgos con su evidencia |
| Perform Risk Analysis | Exposición cualitativa; ningún riesgo dependiente de Windows se cierra con evidencia de Linux |
| Plan Risk Responses | Mitigación por iteración y por unidad |
| Implement Risk Responses | Las unidades del plan nombran los riesgos que neutralizan |
| Monitor Risks | Revisión al cerrar cada iteración |

### 4.8 Áreas de enfoque y gestión del producto

Las cinco áreas de enfoque (inicio, planificación, ejecución, seguimiento y control, cierre) se aplican por iteración, no por proyecto completo. La gestión del producto (PMBOK 8, §2.3) es continua y sobrevive a los proyectos: por eso tiene un espacio propio ([gestión del producto](../product-management/business-model-and-case.md)) y su hoja de ruta no es el cronograma del proyecto.

## 5. Control de cambios

1. **Qué es un cambio:** modificar una línea base (§6), aceptar o retirar un caso de uso, una regla o un requisito, cambiar una dependencia fijada, aceptar un ADR o autorizar trabajo fuera de la iteración en curso.
2. **Quién propone:** cualquier rol; el Agente redacta la propuesta con su evidencia y su impacto.
3. **Quién decide:** el Responsable. Una propuesta queda marcada (`propuesto`, «Candidato», «Pendiente») hasta su decisión, y la verificación impide mezclarla con lo aprobado.
4. **Registro:** el registro de cambios (§7.3) y el de decisiones (§8).
5. **Aceptar no es autorizar:** un caso de uso aceptado entra en el alcance del producto; implementarlo exige que su unidad esté en una iteración autorizada.

## 6. Líneas base

| Línea base | Artefacto | Contenido |
|---|---|---|
| Alcance del producto | Visión y modelo de casos de uso | 30 casos aceptados, las reglas aprobadas y los requisitos aceptados |
| Candidatos | Modelo de casos de uso, §4.3 | Objetivos documentados pendientes de aprobación |
| Alcance de publicación propuesto | [Hoja de ruta](../product-management/product-roadmap.md#3-alcance-de-publicación-propuesto) | Propuesta, no aprobada |
| Alcance de la iteración E3 | Plan de E3 (unidades U1 a U16) | Planificado; ejecución no autorizada |
| Hoja de ruta posterior | Hoja de ruta, unidad Roadmap | Candidatos con «Horizonte: futuro» |
| Decisiones pendientes | Registro de decisiones (§8) | Estado «Pendiente» |
| Dependencias | Plan de E3, §3 | Grafo de unidades sin ciclos |

## 7. Registros

### 7.1 Supuestos

| Supuesto | Origen | Cómo se valida |
|---|---|---|
| Chaquopy es la alternativa prioritaria para Android | Instrucción 2.6.0; documentación oficial de Chaquopy y Electron Cash en producción | Experimento de Android cuando se autorice |
| La reutilización de modelos entre jobs de IA reduce el coste | Hipótesis (instrucción 2.6.0, §111) | Medición en un candidato de IA cuando se cualifique |
| El periodo inicial de 15 días se puede aplicar en todas las plataformas con los mecanismos de cada canal | Modelo comercial aprobado | Condiciones comerciales pendientes y políticas de cada canal |
| SQLite basta para las peticiones externas y el registro de jobs | ADR-0034 | E3 |

### 7.2 Incidencias

| Incidencia | Estado |
|---|---|
| La evidencia de GreenTuber proviene de APK modificados; no sirve para mecanismos comerciales | Registrada; excluida del análisis comercial ([análisis de requisitos, §16.5](../requirements/requirements-analysis.md#165-mecanismos-comerciales)) |
| La versión de Google Play de GreenTuber no está disponible para análisis | Abierta; la capacidad de descarga en esa versión es una declaración del Responsable |

### 7.3 Cambios

| Instrucción | Cambio | Decisión |
|---|---|---|
| 2.6.0 | UC-29 a UC-32 pasan de candidato a aceptado | Aprobado por el Responsable |
| 2.6.0 | Las ampliaciones de flujos de la 2.5.0 pasan a aceptadas | Aprobado como orientación de alcance |
| 2.6.0 | BR-46 a BR-52 pasan a aprobadas con redacción revisada | Aprobado |
| 2.6.0 | D-22, D-23 y D-24 se resuelven | Aprobado |
| 2.6.0 | Nuevos candidatos de IA y comerciales con «Horizonte: futuro» | Pendiente de aprobación |

### 7.4 Lecciones aprendidas

| Lección | Origen | Práctica adoptada |
|---|---|---|
| Una deducción no es un hecho | Corrección del Responsable sobre Google Play (2.5.0) | Separar hecho, declaración e hipótesis; ninguna hipótesis se convierte en restricción |
| Un clon superficial oculta documentos borrados | Corrección del Responsable sobre VidBee (2.5.0) | Historia completa y revisión de rutas borradas en cada referencia |
| Analizar flujos y objetivos, no binarios | Corrección del Responsable sobre los APK | La ausencia de bibliotecas nativas en un APK no es un hallazgo |
| Los APK modificados se analizan estáticamente, sin excluirlos | Corrección del Responsable (2.6.0) | Solo análisis estático; nunca instalar ni ejecutar; sin procedimientos para eludir pagos |
| En la 2.6.0 se presentaron como hechos deducciones sobre GreenTuber (fork sin monetización, capa «injertada», «builds de Aptoide», facturación activa en las dos versiones) | Corrección del Responsable (2.6.0) | Cada afirmación lleva su fuente (manifiesto, firma, cadena); lo no comprobable se declara «no determinable» |

## 8. Registro de decisiones

Las decisiones se definen y argumentan en el [análisis de requisitos](../requirements/requirements-analysis.md); aquí se registra su estado y la responsabilidad que decide. La verificación exige una fila por cada decisión definida.

<!-- decision-register:start -->
| D | Decisión | Responsabilidad | Estado |
|---|---|---|---|
| D-1 | Cookies: archivo del User, perfiles y selección por job y por sitio | Requisitos | Aprobada |
| D-2 | Continuidad selectiva cuando nada es elegible | Requisitos | Aprobada |
| D-3 | Ritmo de peticiones con las capacidades nativas de yt-dlp | Requisitos | Aprobada |
| D-4 | Restricciones temporales con política limitada y configurable | Requisitos | Aprobada |
| D-5 | Almacenamiento preventivo adaptativo | Requisitos | Aprobada |
| D-6 | Pausa gradual e inmediata recuperable | Requisitos | Aprobada |
| D-7 | Proxy: sistema, directo y explícito | Requisitos | Aprobada |
| D-8 | Administración de dependencias controlada y reversible | Arquitectura | Aprobada |
| D-9 | Recuperación local primero | Arquitectura | Aprobada |
| D-10 | Directos y programados dentro del alcance | Requisitos | Aprobada |
| D-11 | Purga: registros y archivos separados | Requisitos | Aprobada |
| D-12 | Fallos de almacenamiento clasificados | Requisitos | Aprobada |
| D-13 | Programación propia | Requisitos | Aprobada |
| D-14 | Avisos configurables | Requisitos | Aprobada |
| D-15 | Cero, uno o N resultados por job | Arquitectura | Aprobada |
| D-16 | Identidad del contenido separada de la del resultado | Arquitectura | Aprobada |
| D-17 | Integración transversal; CLI primero | Arquitectura | Aprobada |
| D-18 | Transformaciones ligadas a la obtención | Requisitos | Aprobada |
| D-19 | Perfiles fijados al encolar | Requisitos | Aprobada |
| D-20 | Ancho de banda individual y global | Requisitos | Aprobada |
| D-21 | Retención y privacidad diferenciadas | Requisitos | Aprobada |
| D-22 | Reemplazo de archivos solo por petición explícita | Requisitos | Aprobada |
| D-23 | Consumo e IA descompuestos en objetivos distintos | Gestión del producto | Aprobada |
| D-24 | Modelo comercial y canales separados por responsabilidad | Gestión del producto | Aprobada |
| D-25 | Periodo inicial: inicio, duración, reinstalación, sin conexión, vencimiento | Gestión del producto | Pendiente |
| D-26 | Adquisición del modo sin anuncios: modalidad, precio, alcance, restauración, reembolsos | Gestión del producto | Pendiente |
| D-27 | Canales por plataforma y Windows tras el periodo inicial | Publicación y distribución | Pendiente |
| D-28 | Inferencia y costes de la IA | Gestión del producto | Pendiente |
<!-- decision-register:end -->
