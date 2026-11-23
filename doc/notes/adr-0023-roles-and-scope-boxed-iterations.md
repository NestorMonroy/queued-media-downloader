# ADR-0023: Roles e iteraciones delimitadas por alcance

- **Estado:** Aceptada
- **Fecha:** 2026-11-23
- **Ajusta:** el tamaño de una tarea definido en [ADR-0022](adr-0022-hybrid-approach-and-task-decomposition.md)

## Contexto

El plan de E1 dejaba abierta su duración, y ADR-0022 limitaba cada tarea a "un PR de menos de un día". Las dos ideas suponían que una persona implementa el código. En este proyecto, la implementación la hace un asistente de IA, y la intervención humana se concentra en decidir, revisar, integrar y evaluar en Windows.

Además, los documentos no deben depender de quién ni de qué herramienta hace cada cosa: deben seguir siendo válidos si cambia la persona o el asistente.

## Decisión

1. **Tres roles**, nombrados en todos los documentos en lugar de personas o productos:
   - **Responsable del proyecto:** decide alcance y prioridades, acepta los ADR, revisa e integra los *pull requests* y decide el cierre de cada iteración.
   - **Agente de implementación:** redacta artefactos, propone ADR, escribe pruebas y código con TDD, ejecuta las comprobaciones locales y abre *pull requests*. No integra en `main`, no acepta ADR y no ejecuta las pruebas `windows`.
   - **Evaluador en Windows:** ejecuta las pruebas `windows`, las verificaciones manuales y las mediciones al cerrar cada iteración. Puede ser la misma persona que el Responsable.
2. **Iteraciones delimitadas por alcance:** una iteración se cierra cuando cumple sus criterios de evaluación, no al agotar un plazo. El avance se mide en tareas terminadas sobre el total.
3. **Tamaño de una tarea:** un *pull request* que el Responsable del proyecto pueda revisar de una sentada, normalmente un cambio en un solo componente con sus pruebas. Sustituye a "menos de un día".
4. **Iteraciones que crecen:** se dividen moviendo slices a la siguiente iteración; no se alargan indefinidamente.

## Consecuencias

- El plan de E1 asigna un rol a cada tarea: el Responsable crea el repositorio (T01) y confirma la licencia de `doc/reference/` (T05); el Evaluador cierra la iteración (T19); el Agente hace el resto.
- El cuello de botella del proyecto es la revisión humana: tareas más pequeñas implican revisiones más rápidas y fiables.
- El [caso de desarrollo](../process/development-case.md#5-roles-y-duración-de-las-iteraciones) y el [vocabulario](../design/00-vocabulary.md) incorporan los tres roles.
