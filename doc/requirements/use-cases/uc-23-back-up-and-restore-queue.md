# UC-23: Respaldar y restaurar la cola

- **Objetivo:** el User conserva una copia coherente del estado de la cola y la recupera en la misma instalación si la base de datos se daña, sin que la restauración cambie la propiedad de los archivos ni haga creer que algo está descargado cuando no lo está.
- **Actor principal:** User
- **Disparador:** antes de un cambio arriesgado (actualizar el programa, mover la carpeta de estado) o tras dañarse la base de datos.
- **Relación:** UC-06 A8 describe hoy la restauración de una copia antigua hecha a mano; este caso de uso la convierte en una operación del producto. UC-22 resuelve el traslado entre instalaciones.
- **Prioridad:** baja
- **Significativo para la arquitectura:** sí: copia coherente con `run` activo y restauración con el owner token
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: parcial (el owner token y las reclamaciones protegen una base de datos restaurada, UC-06 A8; el respaldo no existe). Condiciones técnicas: D-9 y D-21.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:**
  - **Revisión de las restricciones de UC-06 A8:** restaurar a mano es una limitación, no una necesidad satisfecha.
  - **SQLite:** su API de copia de seguridad hace una copia coherente con la base de datos abierta.

## Breve descripción

`backup` crea una copia coherente de la base de datos y de las reclamaciones, con su versión de esquema y la fecha. `restore` reemplaza el estado por una copia, conservando la anterior. Al arrancar tras restaurar, la recuperación (UC-06) concilia la copia con los archivos reales usando el owner token: nada se hereda por coincidir el id.

## Precondiciones

- UC-01 completado. Para `restore`, `run` no está en ejecución.

## Flujo básico

1. El User ejecuta `backup [CARPETA]`.
2. El sistema copia la base de datos con la API de copia de seguridad de SQLite, también si `run` está activo, y copia las reclamaciones.
3. El sistema verifica la copia (integridad de SQLite) y muestra su ruta y su tamaño.

## Flujos alternativos

- **A1. Restaurar:** `[estado: ausente]` `restore COPIA` comprueba la integridad y la versión de esquema, renombra el estado actual como copia, coloca la restaurada y aplica las migraciones pendientes.
- **A2. Primer `run` tras restaurar:** `[estado: ausente]` UC-06, con A8 (base de datos restaurada) y A11 (evidencia local). Un job `COMPLETED` cuyo archivo no está sigue UC-06 A9. Ningún archivo se toma como propio sin su reclamación con el owner token correspondiente.
- **A3. Respaldo periódico** `[estado: ausente]` (si D-13 lo programa): retención de las últimas `N` copias, sin un valor fijado.

## Excepciones

- **E1. Copia dañada o de un esquema más nuevo que el programa:** `[estado: ausente]` no se restaura nada; código `2`.
- **E2. `run` en ejecución durante `restore`:** `[estado: ausente]` se rechaza; código `1`.
- **E3. Sin espacio para la copia:** `[estado: ausente]` UC-17; no queda ninguna copia a medias.

## Garantías

- **De éxito:** una copia coherente y verificada, o un estado restaurado y conciliado.
- **Mínima:** restaurar nunca borra el estado anterior ni cambia archivos descargados.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-17, BR-19 y BR-36.
- **Requisitos suplementarios:** SUP-R01 y SUP-R12.
- **Restricciones:** el respaldo no contiene secretos (BR-34); restaura la misma instalación, no traslada (UC-22).
- **Dependencias:** UC-06 y UC-17.

## Criterios de aceptación

1. Un respaldo hecho con `run` activo pasa la comprobación de integridad de SQLite.
2. Tras restaurar, ningún job hereda la propiedad de un archivo sin su reclamación y su owner token.
3. Una restauración fallida deja el estado anterior intacto.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Respaldo con escrituras concurrentes; restauración y conciliación | Cualquier sistema |
| Restaurar una copia con ids reutilizados (UC-06 A8) | Cualquier sistema |
