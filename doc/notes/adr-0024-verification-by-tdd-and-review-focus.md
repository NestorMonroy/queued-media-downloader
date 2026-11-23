# ADR-0024: Verificación por TDD y revisión centrada en las pruebas

- **Estado:** Aceptada
- **Fecha:** 2026-11-23
- **Corrige:** una consecuencia de [ADR-0023](adr-0023-roles-and-scope-boxed-iterations.md) ("el cuello de botella del proyecto es la revisión humana")

## Contexto

ADR-0023 afirmó que la revisión humana sería el cuello de botella del proyecto. La afirmación ignoraba que el proyecto usa TDD ([ADR-0021](adr-0021-tdd-and-windows-validation-without-ci.md)) y cinco comprobaciones automáticas ([ADR-0019](adr-0019-code-quality-tools.md)): con ellas, el Responsable del proyecto no tiene que verificar línea a línea que el código funciona.

Lo que las herramientas no pueden verificar es si **las pruebas expresan lo que se pidió**. Si el Agente de implementación entiende mal un requisito, escribirá una prueba equivocada y un código que la pasa: TDD comprueba que el código cumple las pruebas, no que las pruebas cumplan la intención.

## Decisión

1. **La corrección del código la verifican las pruebas y las herramientas**, no la revisión humana: `pytest` (comportamiento), `ruff` (formato y estilo), `mypy` (tipos) y `lint-imports` (reglas de dependencia).
2. **La revisión del Responsable del proyecto se centra en lo que las herramientas no ven:**
   - que cada prueba exprese el criterio "Terminada cuando" de su tarea y el escenario del caso de uso correspondiente;
   - que los nombres sigan el vocabulario y que el diseño respete los ADR.
3. **El tamaño de una tarea** (un *pull request* que se revise de una sentada, ADR-0023) se mantiene, con otro motivo: unas pocas pruebas que se pueden contrastar con su criterio, no un volumen de código.

## Consecuencias

- Los puntos que requieren intervención humana son las **decisiones** (aceptar ADR, cerrar iteraciones) y la **evaluación en Windows**. Ahí puede haber esperas; la revisión de código no es el cuello de botella.
- Los criterios de terminado del plan de iteración y los escenarios de prueba de cada caso de uso son la referencia de la revisión: deben estar escritos antes de que empiece la tarea.
