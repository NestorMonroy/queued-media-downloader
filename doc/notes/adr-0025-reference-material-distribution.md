# ADR-0025: Distribución del material de referencia

- **Estado:** Aceptada
- **Fecha:** 2026-11-23
- **Resuelve:** la tarea T05 del [plan de E1](../project-management/iteration-plan-e1.md) y la parte de `doc/reference/` del riesgo R-12

## Contexto

`doc/reference/` contiene las guías de clean code y los principios de nombres que [ADR-0011](adr-0011-code-conventions.md) hace obligatorios. El plan de E1 incluía una tarea (T05) para confirmar si ese material podía distribuirse dentro del repositorio.

## Decisión

El Responsable del proyecto confirma que el material de `doc/reference/` se distribuye con el proyecto. No requiere una entrada propia en la sección de componentes de terceros de `LICENSE`.

## Consecuencias

- La tarea T05 se elimina del plan de E1, que queda con 18 tareas. Los identificadores del resto no cambian.
- El riesgo R-12 queda limitado al cumplimiento de la LGPL de ffmpeg.
- El requisito SUP-L03 queda cumplido.
