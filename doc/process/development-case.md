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
| **Elaboración** | E1, E2, E3 | Arquitectura del ciclo de vida | Los seis casos de uso significativos funcionan de extremo a extremo; los riesgos R-01 a R-06 están neutralizados; las pruebas `windows` pasan en Windows |
| **Construcción** | C1… (según el plan de desarrollo) | Capacidad operativa inicial | UC-07 a UC-10 implementados; procedimiento de actualización de yt-dlp documentado; README de instalación verificado en Windows |
| **Transición** | T1 | Entrega del producto | Instalación desde un clon nuevo por una persona ajena al desarrollo, en Windows |

| Iteración | Casos de uso | Riesgos |
|---|---|---|
| E1 | UC-01, UC-02, UC-03 (flujo básico) | R-01, R-02, R-03, R-12 |
| E2 | UC-05, UC-06; flujos alternativos de UC-03 | R-04, R-05, R-10 |
| E3 | UC-04 | R-06 |

## 2. Artefactos

| Disciplina | Artefacto | Ubicación | Cuándo se actualiza |
|---|---|---|---|
| Requisitos | Visión | [requirements/vision.md](../requirements/vision.md) | Si cambia el alcance |
| Requisitos | Modelo de casos de uso y especificaciones | [requirements/](../requirements/use-case-model.md) | Antes de la iteración que implementa cada caso de uso |
| Requisitos | Especificación complementaria | [requirements/supplementary-specification.md](../requirements/supplementary-specification.md) | Si aparece un requisito transversal |
| Requisitos | Glosario | [design/00-vocabulary.md](../design/00-vocabulary.md) | Antes de usar un concepto nuevo |
| Análisis y diseño | Documento de arquitectura | [design/](../design/01-architecture.md) | Al cambiar la estructura o un flujo |
| Análisis y diseño | Decisiones de arquitectura (ADR) | [notes/](../notes/README.md) | En cada decisión; las aceptadas no se editan |
| Gestión del proyecto | Lista de riesgos | [project-management/risk-list.md](../project-management/risk-list.md) | Al cerrar cada iteración |
| Gestión del proyecto | Plan de iteración (slices, tareas y camino crítico) | `project-management/iteration-plan-<id>.md` | Al empezar cada iteración; se completa con su evaluación al cerrarla |
| Entorno | Caso de desarrollo | Este documento | Si cambia el proceso |
| Implementación y pruebas | Código, pruebas y configuración | `queued_media_downloader/`, `tests/`, `pyproject.toml` | Continuo |

No se usan: modelo de negocio, caso de negocio, modelo de análisis separado del diseño, plan de despliegue separado (el despliegue es el README) ni plan de gestión de configuración separado (lo cubre [ADR-0020](../notes/adr-0020-repository-branching-and-lfs.md)).

## 3. Prácticas

### Implementación

- **TDD:** prueba primero, código mínimo, refactorización ([ADR-0021](../notes/adr-0021-tdd-and-windows-validation-without-ci.md)).
- **Convenciones:** vocabulario, identificadores en inglés, docstrings y comentarios en español, [guías de clean code](../reference/clean-code-guidelines/README.md) y [principios de nombres](../reference/naming-principles/clean-code-naming-principles.md) ([ADR-0011](../notes/adr-0011-code-conventions.md), [ADR-0019](../notes/adr-0019-code-quality-tools.md)).
- **Ramas:** *trunk-based*, ramas cortas, integración por *pull request* ([ADR-0020](../notes/adr-0020-repository-branching-and-lfs.md)).

### Comprobaciones locales antes de integrar en `main`

```text
uv run ruff format --check
uv run ruff check
uv run mypy
uv run lint-imports
uv run pytest
```

### Cierre de cada iteración (evaluación)

1. El Evaluador en Windows ejecuta `uv run pytest -m windows` en el entorno Windows.
2. Ejecutar las verificaciones manuales de Windows que indique el plan de la iteración.
3. Medir la memoria (RSS máxima) indicada en el plan.
4. Comparar el resultado con los criterios de evaluación del plan.
5. Actualizar la lista de riesgos y registrar las decisiones nuevas como ADR.
6. Escribir la evaluación en el plan de la iteración; el Responsable del proyecto decide si la iteración se cierra.

### Definición de terminado (por cambio)

- El cambio tiene pruebas escritas antes del código.
- Las cinco comprobaciones locales pasan.
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
