# UC-28: Recibir avisos operativos

- **Objetivo:** el User se entera de lo que requiere su atención sin vigilar la consola: la cola terminó, falló un job, la cola se detuvo, hace falta una acción, hay una restricción del sitio o un fallo de almacenamiento. Puede elegir qué avisos recibe y sin que se repitan.
- **Actor principal:** User
- **Actor secundario:** Centro de notificaciones de Windows, u otro mecanismo según D-14
- **Disparador:** un suceso de la cola durante `run`.
- **Relación:**
  - se alimenta de los job events existentes (`JobCompleted`, `JobFailed`, `JobCancelled`) y de los sucesos de UC-11, UC-14, UC-17 y UC-21;
  - complementa el resumen de consola de UC-03, que solo ve quien mira la consola.
- **Prioridad:** baja
- **Significativo para la arquitectura:** no; un consumidor más de los job events
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: ausente. Condición técnica: D-14.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:**
  - **Seal:** notificaciones por descarga y al terminar.
  - **Revisión de exclusiones:** «`run` ya resume al terminar» no avisa a quien no mira la consola ([análisis, §12](../requirements-analysis.md#12-reconciliación-de-exclusiones)).

## Breve descripción

`run` emite avisos para los sucesos elegidos y agrupa los repetidos ([BR-39](../business-rules.md)): un aviso por condición, no por job. Las preferencias (qué sucesos se avisan y por qué medio) son configuración (UC-20). El canal concreto depende de D-14: notificación de Windows, archivo de sucesos legible por otros programas, o ambos.

No incluye correo, servicios de mensajería ni ejecutar comandos del User al recibir un suceso.

## Precondiciones

- `run` en ejecución.

## Flujo básico

1. Un suceso configurado ocurre (por ejemplo, la cola terminó).
2. El sistema comprueba si ya avisó de ese mismo suceso en el intervalo de agrupación ([BR-39](../business-rules.md)).
3. El sistema emite un aviso con el suceso, su alcance (job, sitio, unidad o cola) y, si hace falta, la acción esperada.

## Flujos alternativos

- **A1. Varios jobs fallan por la misma causa:** `[estado: ausente]` un solo aviso con el número de jobs.
- **A2. Suceso que requiere intervención** `[estado: ausente]` (un acceso caducado, una carpeta inválida, un extractor desactualizado): el aviso incluye la acción.
- **A3. Preferencias:** `[estado: ausente]` `config set notifications ...` (UC-20); por omisión, solo la cola terminada y lo que requiere intervención.
- **A4. Archivo de sucesos** `[estado: ausente]` (si D-14 lo incluye): una línea JSON por suceso en la carpeta de estado, para otros programas (SUP-I01).

## Excepciones

- **E1. El mecanismo de avisos no está disponible** `[estado: ausente]` (por ejemplo, sesión sin escritorio): el aviso se escribe en el log y la cola sigue.

## Garantías

- **De éxito:** el User recibe un aviso por suceso relevante.
- **Mínima:** un fallo al avisar nunca detiene ni cambia la cola.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-11 y BR-39.
- **Requisitos suplementarios:** SUP-U04, SUP-I01 y SUP-SEC01 (sin secretos en los avisos).
- **Restricciones:** sin servicios externos ni ejecución de comandos.
- **Dependencias:** UC-03, UC-11, UC-14, UC-17, UC-20 y UC-21; D-14.

## Criterios de aceptación

1. Con 10 jobs que fallan por la misma restricción del sitio, se emite un solo aviso.
2. Un fallo del mecanismo de avisos no cambia el resultado de `run`.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Agrupación y preferencias con un emisor falso | Cualquier sistema |
| Notificación real de Windows | **Windows** |
