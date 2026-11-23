# ADR-0022: Enfoque híbrido y descomposición del trabajo en slices

- **Estado:** Aceptada
- **Fecha:** 2026-11-23
- **Nota:** el tamaño de una tarea ("menos de un día") y la duración de las iteraciones se redefinen en [ADR-0023](adr-0023-roles-and-scope-boxed-iterations.md).

## Contexto

El proyecto usa RUP ([caso de desarrollo](../process/development-case.md)). En la práctica combina dos maneras de trabajar:
- **Predictiva:** fases con hitos, Visión, modelo de casos de uso, arquitectura y ADR definidos antes de construir, lista de riesgos y planes de iteración con criterios de evaluación.
- **Ágil:** iteraciones cortas con software ejecutable, TDD, ramas cortas con *pull requests* y evaluación al cerrar cada iteración que ajusta el plan.

Para planificar la iteración E1 se analizó la técnica de *Task Decomposition* con tres enfoques de un ejemplo de migración de WPF a PyQt:
1. **Por capas arquitectónicas:** terminar cada capa antes de la siguiente. Contradice la estructura por componentes ([ADR-0016](adr-0016-component-packages-and-flat-layout.md)) y retrasa la integración: nada funciona de extremo a extremo hasta el final.
2. **Por componentes o funcionalidades** (deducido; el texto llegó incompleto): útil en el nivel de las tareas.
3. **Por fases iterativas con un MVP:** encaja con las fases e iteraciones de RUP, pero en Elaboración las iteraciones se eligen por riesgo, no por funcionalidad mínima.

## Decisión

1. **El enfoque del proyecto es híbrido.** Se fija de antemano lo que es caro cambiar (alcance, arquitectura, contratos entre componentes, plataforma, licencias) y se decide durante la iteración lo que es barato cambiar (implementación interna de un componente, orden de las tareas de un slice).
2. **Descomposición en cuatro niveles:** fase → iteración (por riesgo o por casos de uso) → **slice** (incremento ejecutable de extremo a extremo de un escenario de caso de uso) → **tarea** (un cambio en un componente con TDD, con una prueba como criterio de terminado, en un PR de menos de un día).
3. **Término *slice*** en lugar de su traducción, añadido al [vocabulario](../design/00-vocabulary.md) junto con *phase*, *iteration* y *task*. *Task* es un concepto del proceso y nunca sinónimo de *job*.
4. **No se descompone por capas técnicas.** El primer slice de un proyecto prepara el entorno; los demás implementan escenarios de casos de uso.

## Consecuencias

- El [plan de E1](../project-management/iteration-plan-e1.md) queda descompuesto en cinco slices (entorno, encolar, descargar sin unir, descargar uniendo, diagnosticar) y 19 tareas con dependencias y camino crítico.
- A mitad de E1 (tarea T15) ya hay una descarga de extremo a extremo; los riesgos de integración aparecen pronto.
- Cada plan de iteración incluye sus slices, sus tareas y su camino crítico.
