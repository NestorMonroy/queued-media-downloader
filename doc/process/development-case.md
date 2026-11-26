# Caso de desarrollo

- **Versión:** 1.0
- **Fecha:** 2026-11-23

Adaptación de RUP a este proyecto: qué fases, artefactos y prácticas se usan, y cómo. El proyecto lo desarrolla un equipo pequeño, así que la adaptación es ligera: cada artefacto existe porque alguien lo va a leer o usar.

---

## 0. Enfoque del proyecto: híbrido

El proyecto combina una parte **predictiva** y una parte **ágil** ([ADR-0022](../notes/adr-0022-hybrid-approach-and-task-decomposition.md)):

| Parte predictiva (se planifica y documenta antes) | Parte ágil (se adapta durante la ejecución) |
|---|---|
| Fases de RUP con hitos de cierre definidos | Iteraciones cortas que terminan en software ejecutable |
| Visión, modelo de casos de uso y especificación complementaria | Slices verticales de extremo a extremo dentro de cada iteración |
| Arquitectura y decisiones registradas (ADR) antes de construir | TDD: prueba primero, código mínimo, refactorización |
| Lista de riesgos que ordena las iteraciones | Ramas cortas, *pull requests* e integración frecuente en `main` |
| Plan de cada iteración con alcance y criterios de evaluación | Evaluación al cerrar cada iteración que ajusta riesgos, plan y decisiones |

Regla de equilibrio: se fija de antemano **lo que es caro cambiar** (alcance, arquitectura, contratos entre componentes, plataforma, licencias) y se decide durante la iteración **lo que es barato cambiar** (implementación interna de un componente, orden de las tareas dentro de un slice).

---

## 1. Fases e hitos

| Fase | Iteraciones | Hito de cierre | Criterio |
|---|---|---|---|
| **Inicio** | 1 (completada con este conjunto de artefactos) | Objetivos del ciclo de vida | Visión, casos de uso significativos, riesgos y plan de E1 revisados y aceptados |
| **Elaboración** | E1, E2 (E3 solo si la evaluación de E2 deja riesgos sin neutralizar) | Arquitectura del ciclo de vida | Los seis casos de uso significativos funcionan de extremo a extremo; los riesgos R-01 a R-06 están neutralizados; las pruebas `windows` pasan en Windows |
| **Construcción** | C1… (según el plan de desarrollo) | Capacidad operativa inicial | UC-07 a UC-10 implementados; procedimiento de actualización de yt-dlp documentado; README de instalación verificado en Windows |
| **Transición** | T1 | Entrega del producto | Instalación desde un clon nuevo por una persona ajena al desarrollo, en Windows |

| Iteración | Casos de uso | Riesgos |
|---|---|---|
| E1 | UC-01, UC-02, UC-03 (flujo básico) | R-01, R-02, R-03, R-12 |
| E2 | UC-04, UC-05, UC-06; flujos alternativos de UC-03; **UC-07 a UC-10** (ajuste, abajo) | R-02, R-04, R-05, R-06, R-10, R-14 |

### Ajuste de 2026-11-25: UC-07 a UC-10 entran en E2

El Responsable del proyecto decidió implementar en E2 los casos de uso restantes y validar Windows en una sola campaña final (T42), en lugar de evaluar E2 primero. Consecuencias sobre este caso de desarrollo:

- **Construcción** ya no tiene que implementar UC-07 a UC-10; conserva el procedimiento de actualización de yt-dlp, el README verificado en Windows y lo que deje abierto la evaluación de E2.
- **El hito de Elaboración** (arquitectura del ciclo de vida) y la **capacidad operativa** de UC-07 a UC-10 se deciden con la misma campaña: un defecto en Windows de un caso de uso no significativo no bloquea el hito de arquitectura, pero sí su aceptación (§3, estados del producto).
- **La evaluación de cierre** (§3) se hace una sola vez, sobre un commit identificado, con la campaña de [windows-validation-campaign.md](../project-management/windows-validation-campaign.md); las correcciones que provoque siguen el procedimiento de regresión de esa guía.
- La evidencia de Windows de E1 (2026-11-23) se conserva como evidencia de E1; **no** valida la build actual, que cambió desde entonces, y la campaña la repite.

## 2. Artefactos

| Disciplina | Artefacto | Ubicación | Cuándo se actualiza |
|---|---|---|---|
| Requisitos | Visión | [requirements/vision.md](../requirements/vision.md) | Si cambia el alcance |
| Requisitos | Modelo de casos de uso y especificaciones | [requirements/](../requirements/use-case-model.md) | Antes de la iteración que implementa cada caso de uso |
| Requisitos | Especificación complementaria | [requirements/supplementary-specification.md](../requirements/supplementary-specification.md) | Si aparece un requisito transversal |
| Requisitos | Glosario | [design/00-vocabulary.md](../design/00-vocabulary.md) | Antes de usar un concepto nuevo |
| Requisitos | Reglas de negocio y sus parámetros | [requirements/business-rules.md](../requirements/business-rules.md) | Al decidir o cambiar una regla |
| Requisitos | Catálogo de condiciones de fallo | [requirements/failure-conditions.md](../requirements/failure-conditions.md) | Al encontrar una condición nueva o cambiar su tratamiento |
| Requisitos | Análisis de requisitos (evidencia, referencias, decisiones pendientes) | [requirements/requirements-analysis.md](../requirements/requirements-analysis.md) | Al analizar un cambio de requisitos |
| Requisitos | Modelo de casos de uso de la validación | [process/validation-use-case-model.md](validation-use-case-model.md) | Si cambia la campaña de Windows |
| Análisis y diseño | Documento de arquitectura: vigente (Partes 1 y 2) y objetivo (Parte 3: contratos públicos, capacidades por ambiente, realización de los casos de uso, aplicabilidad por plataforma, matriz de evolución) | [design/](../design/01-architecture.md), [Parte 3](../design/03-target-architecture-and-evolution.md) | Al cambiar la estructura o un flujo; la Parte 3, al cambiar un contrato o la evaluación de una plataforma |
| Análisis y diseño | Decisiones de arquitectura (ADR) | [notes/](../notes/README.md) | En cada decisión; las aceptadas no se editan |
| Gestión del proyecto | Lista de riesgos | [project-management/risk-list.md](../project-management/risk-list.md) | Al cerrar cada iteración |
| Gestión del proyecto | Plan de iteración (slices, tareas y camino crítico) | `project-management/iteration-plan-<id>.md` | Al empezar cada iteración; se completa con su evaluación al cerrarla. El plan de la iteración siguiente puede publicarse antes de autorizarla, con su estado («planificada, ejecución no autorizada») |
| Entorno | Caso de desarrollo | Este documento | Si cambia el proceso |
| Implementación y pruebas | Código, pruebas y configuración | `queued_media_downloader/`, `tests/`, `pyproject.toml` | Continuo |

### Requisitos: RUP con técnicas de BABOK v3

La disciplina de Requisitos de RUP produce los artefactos de la tabla; BABOK v3 aporta las técnicas con las que se elaboran:
- **Elicitación y análisis:** análisis de documentos (10.18), benchmarking de proyectos de referencia (10.4), descomposición funcional (10.22), análisis de interfaces (10.24) y análisis de causa raíz (10.40).
- **Especificación:** casos de uso y escenarios (10.47), con el formato común del [modelo, §2](../requirements/use-case-model.md#2-formato-de-los-casos-de-uso); reglas de negocio separadas de los flujos y de sus parámetros (10.9); requisitos no funcionales con criterio verificable (10.30); glosario (10.21).
- **Decisión y priorización:** modelado de decisiones (10.16) con alternativas y recomendación, sin aprobarlas en el análisis; priorización (10.33).
- **Verificación:** características de BABOK 7.2 y criterios de aceptación (10.1) en cada caso de uso.

Reglas del modelo:
- la matriz de completitud no se edita a mano: la genera `scripts/check_requirements_model.py --write`, y `run_checks` comprueba que esté al día;
- un solo modelo canónico: los hallazgos de una referencia se integran en sus artefactos, nunca en catálogos paralelos con identificadores propios;
- los identificadores de los casos de uso no se renumeran; un caso de uso retirado conserva su id, que no se reutiliza;
- cada concepto tiene una sola autoridad, y los demás documentos la enlazan;
- **un modelo para todas las interfaces y plataformas** (ADR-0032): una GUI o una aplicación móvil no crean casos de uso propios. Sus diferencias se expresan como escenarios, restricciones, requisitos suplementarios, capacidades y criterios de aceptación, y la aplicabilidad de cada caso de uso por plataforma vive en la Parte 3 del diseño, §13, que el script del modelo comprueba.

### Análisis y diseño: arquitectura multiplataforma

- **Evidencia con su nivel:** código, inventario reproducible, referencia, documental, inferido o pendiente ([Parte 3](../design/03-target-architecture-and-evolution.md)). Una capacidad inferida no se declara demostrada.
- **Inventario estructural:** se obtiene con `scripts/experiments/architecture_inventory.py`; los documentos citan sus conteos, no los copian a mano en catálogos paralelos.
- **Reglas de dependencia:**
  - una regla de arquitectura entra en `lint-imports` cuando el código actual ya la cumple;
  - las reglas objetivo se documentan con su criterio de activación (Parte 3, §9.1);
  - ninguna regla vigente se desactiva.
- **Pruebas compartidas y específicas:**
  - los criterios de aceptación de un caso de uso son los mismos en todas las plataformas;
  - las pruebas de contrato se ejecutan en cualquier sistema;
  - las de cada capacidad, con la marca de su plataforma;
  - cada evidencia identifica plataforma, versión y commit.

No se usan: modelo de negocio, caso de negocio, modelo de análisis separado del diseño, plan de despliegue separado (el despliegue es el README) ni plan de gestión de configuración separado (lo cubre [ADR-0020](../notes/adr-0020-repository-branching-and-lfs.md)).

## 3. Prácticas

### Implementación

- **TDD:** prueba primero, código mínimo, refactorización ([ADR-0021](../notes/adr-0021-tdd-and-windows-validation-without-ci.md)).
- **Convenciones:** vocabulario, identificadores en inglés, docstrings y comentarios en español, [guías de clean code](../reference/clean-code-guidelines/README.md) y [principios de nombres](../reference/naming-principles/clean-code-naming-principles.md) ([ADR-0011](../notes/adr-0011-code-conventions.md), [ADR-0019](../notes/adr-0019-code-quality-tools.md)).
- **Ramas:** *trunk-based*, ramas cortas, integración por *pull request* ([ADR-0020](../notes/adr-0020-repository-branching-and-lfs.md)).

### Propuestas frente a alcance aceptado

- Un flujo propuesto lleva `[estado: ...; propuesto]`; un objetivo nuevo, el estado «candidato» en su especificación. En el plan de E3 ambos tienen el alcance «Propuesto» y en el diseño el candidato tiene el estado «Candidato». `scripts/check_requirements_model.py` impide mezclar propuestas con requisitos aprobados.
- El descubrimiento funcional con referencias registra su evidencia en el análisis de requisitos (§15), con nivel L0 a L5 y localizador; no crea modelos ni identificadores por referencia.

### Comprobaciones locales antes de integrar en `main`

```text
uv run python scripts/run_checks.py
```

Ejecuta, en orden, `ruff format --check .`, `ruff check .`, `mypy`, `lint-imports`, `scripts/check_requirements_model.py` (enlaces, identificadores, matriz de completitud y tablas de realización y aplicabilidad por plataforma) y `pytest`, conserva la salida y el código de salida de cada uno y se detiene en el primero que falla (stop-on-error), con su código. No se usan tuberías ni truncados que oculten el código de salida real. Si alguna falla, no se hace commit, merge ni publicación.

### Cierre de cada iteración (evaluación)

1. El Evaluador en Windows ejecuta `uv run pytest -m windows` en el entorno Windows.
2. Ejecutar las verificaciones manuales de Windows que indique el plan de la iteración.
3. Medir la memoria (RSS máxima) indicada en el plan.
4. Comparar el resultado con los criterios de evaluación del plan.
5. Actualizar la lista de riesgos y registrar las decisiones nuevas como ADR.
6. Escribir la evaluación en el plan de la iteración; el Responsable del proyecto decide si la iteración se cierra.

### Scripts del proyecto

Todos funcionan desde un clon del repositorio, sin herramientas externas al proyecto. Los nombres describen su responsabilidad, no la tarea que los creó.

| Script | Responsabilidad | Alcance |
|---|---|---|
| `scripts/run_checks.py` | Las seis comprobaciones con stop-on-error y el código de salida real de cada una | Reutilizable, cualquier sistema |
| `scripts/check_requirements_model.py` | Enlaces, identificadores y matriz de completitud del modelo de requisitos; cobertura y estados de la realización de los casos de uso y de su aplicabilidad por plataforma (Parte 3 del diseño); cobertura del plan de E3: cada flujo pendiente con una sola unidad, grafo de unidades sin ciclos, reglas y suplementarios pendientes con estrategia (consistencia documental, no evidencia de implementación); `--write` regenera la matriz | Reutilizable, cualquier sistema |
| `scripts/check_commit_message.py` | Convenciones de los mensajes de commit | Reutilizable, cualquier sistema |
| `scripts/windows/validation_campaign.ps1` | Ejecuciones de la validación en Windows identificadas por commit, colas aisladas y evidencia | Reutilizable, Windows |
| `scripts/experiments/process_tree_termination.py` | Experimento de terminación de árboles de procesos (T33, ADR-0029), que la validación repite en Windows | Experimento; sus resultados históricos están en `doc/notes/experiments/` |
| `scripts/experiments/requirements_qualification.py` | Experimentos de cualificación de decisiones de requisitos (reintentos de yt-dlp, copia de SQLite, cadena de causas) | Experimento; resultados en `doc/notes/experiments/requirements-qualification.md` |
| `scripts/experiments/architecture_inventory.py` | Inventario estructural (módulos, clases por tipo, API pública, mecanismos variables, pruebas) y grafo de componentes con grimp | Experimento; resultados en `doc/notes/experiments/architecture-inventory-linux.json` |
| `scripts/experiments/execution_alternatives.py` | Comparación de alternativas de ejecución: arranque, concurrencia, cancelación bloqueada, descendientes, aislamiento ante fallos, event loop, coste de eventos, memoria, programa cliente | Experimento; resultados en `doc/notes/experiments/execution-alternatives.md` |

### Mensajes de commit

Estilo de Tim Pope, en inglés: asunto en imperativo de 50 caracteres como máximo, con mayúscula y sin punto final; una línea en blanco; cuerpo que explica qué y por qué, con líneas de 72 caracteres como máximo. Antes de cada commit:

```text
uv run python scripts/check_commit_message.py RUTA_DEL_MENSAJE
```

### Estados del producto: cinco conceptos distintos

| Estado | Qué significa | Quién lo establece y con qué evidencia |
|---|---|---|
| **Implementación completa** (`IMPLEMENTATION_COMPLETE`) | Todos los escenarios de los casos de uso del alcance están implementados | Agente de implementación; matriz del plan de la iteración |
| **Verificación de desarrollo** (`DEVELOPMENT_VERIFICATION_PASSED`) | Las seis comprobaciones pasan en el entorno de desarrollo (Linux), con las pruebas que no requieren Windows ni red | Agente de implementación; salida de `scripts/run_checks.py` sobre un commit identificado |
| **Validación en la plataforma** (`WINDOWS_VALIDATION_PENDING` / `..._PASSED`) | Las pruebas `windows` y los pasos manuales pasan en Windows 10/11 x64 sobre el commit evaluado | Evaluador en Windows; registro de resultados de la campaña. La evidencia de Linux **nunca** cuenta como validación en Windows |
| **Evaluación de la iteración** | Comparación de los resultados con los criterios del plan, riesgos y decisiones actualizados | Agente de implementación redacta; Responsable del proyecto decide el cierre |
| **Aceptación final** (`FINAL_ACCEPTANCE_PENDING` / `..._ACCEPTED`) | El Responsable del proyecto acepta el producto de la iteración | Responsable del proyecto, solo con los resultados reales de Windows |

Una prueba no ejecutada nunca cuenta como satisfactoria; se informa como pendiente o no ejecutable, con su motivo.

### Definición de terminado (por cambio)

- El cambio tiene pruebas escritas antes del código.
- Las seis comprobaciones locales pasan (`scripts/run_checks.py`), y ninguna prueba toca los datos reales del usuario (la sesión de pruebas falla si cambia algún archivo del estado, de las descargas o de `config.toml` reales).
- Los nombres nuevos están en el vocabulario.
- Si el cambio toma una decisión de arquitectura, hay un ADR.

---

## 4. Descomposición del trabajo

Cada iteración se descompone en cuatro niveles. Los dos primeros son la parte predictiva; los dos últimos, la ágil.

```text
Fase           Inicio, Elaboración, Construcción, Transición
└─ Iteración   Elegida por riesgo (Elaboración) o por casos de uso pendientes (Construcción)
   └─ Slice    Incremento ejecutable de extremo a extremo que implementa un escenario de un caso de uso
      └─ Tarea Un cambio en un componente con TDD
```

Reglas:
- **Cada slice termina en algo que se ejecuta**, no en un componente o una capa terminados. Así los riesgos de integración aparecen pronto.
- **Cada tarea** tiene un identificador (`T01`, `T02`…), un rol responsable, una prueba como criterio de terminado, sus dependencias explícitas, y cabe en un *pull request* que se revise de una sentada ([§5](#5-roles-y-duración-de-las-iteraciones)).
- **El primer slice de un proyecto** prepara el entorno (repositorio, `pyproject.toml`, herramientas); es el único que no implementa un caso de uso.
- **El plan de cada iteración** muestra sus slices, sus tareas y el camino crítico.
- No se descompone por capas técnicas: contradice la estructura por componentes ([ADR-0016](../notes/adr-0016-component-packages-and-flat-layout.md)) y retrasa la integración hasta el final.

---

## 5. Roles y duración de las iteraciones

### Roles

Los documentos nombran roles, nunca productos ni personas: así siguen siendo válidos si cambia la herramienta o quien la usa ([ADR-0023](../notes/adr-0023-roles-and-scope-boxed-iterations.md)).

| Rol | Lo asume | Responsabilidades | No hace |
|---|---|---|---|
| **Responsable del proyecto** | Una persona | Decide alcance y prioridades; acepta o rechaza los ADR; revisa e integra los *pull requests* en `main`; decide el cierre de cada iteración | — |
| **Agente de implementación** | Un asistente de IA | Redacta artefactos y propone ADR; escribe pruebas y código con TDD; ejecuta las comprobaciones locales; abre *pull requests* | No integra en `main`, no acepta ADR y no ejecuta las pruebas `windows` (trabaja en un entorno Linux) |
| **Evaluador en Windows** | Una persona (puede ser el Responsable del proyecto) | Ejecuta `uv run pytest -m windows`, las verificaciones manuales y las mediciones de memoria al cerrar cada iteración; registra los resultados en el plan | — |

Correspondencia con los roles de RUP: el Responsable del proyecto cubre jefe de proyecto, interesado y revisor de arquitectura; el Agente de implementación cubre analista, diseñador, implementador y diseñador de pruebas; el Evaluador en Windows cubre el rol de probador.

### Duración: iteraciones delimitadas por alcance

- **Una iteración se cierra cuando cumple sus criterios de evaluación,** no al agotar un plazo. La velocidad del Agente de implementación no es una medida útil para planificar; las esperas posibles están en las decisiones del Responsable del proyecto y en la evaluación en Windows.
- **El avance se mide en tareas terminadas** sobre el total de la iteración, no en días.
- **Tamaño de una tarea:** un *pull request* que el Responsable del proyecto pueda revisar de una sentada; normalmente un cambio en un solo componente con sus pruebas.
- **Qué revisa el Responsable:** que las pruebas expresen el criterio de terminado y el escenario del caso de uso, y que se respeten el vocabulario y los ADR. La corrección del código la verifican las pruebas y las herramientas ([ADR-0024](../notes/adr-0024-verification-by-tdd-and-review-focus.md)).
- Si una iteración crece más de lo previsto, se divide moviendo slices a la siguiente iteración; no se alarga indefinidamente.
