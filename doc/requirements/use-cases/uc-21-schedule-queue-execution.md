# UC-21: Programar la ejecución de la cola

- **Objetivo:** la cola descarga solo cuando el User lo permite (más tarde, en ciertas horas, de forma recurrente) sin que él tenga que estar presente para iniciarla ni detenerla, y el User puede consultar y cambiar esa programación.
- **Actor principal:** User
- **Actor secundario:** Temporizador (el reloj del sistema; para arrancar sin `run` activo, el Programador de tareas de Windows, D-13)
- **Disparador:** el User quiere descargar de noche, fuera del horario de trabajo o cuando la conexión es más barata o está libre.
- **Relación:** usa el control de ejecución de UC-14 (pausa, continuación, detención) y la admisión de `run`. Convive con los aplazamientos de UC-11 y UC-17: una ventana cerrada no aplaza un job, solo impide enviarlo.
- **Prioridad:** media
- **Significativo para la arquitectura:** sí; la programación es una capacidad del producto (D-13, resuelta funcionalmente)
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: ausente. Condición técnica: D-13.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** revisión de la exclusión «lo cubre el Programador de tareas de Windows»: esa herramienta puede arrancar `run`, pero no ofrece ventanas de descarga ni las combina con la pausa, los aplazamientos y la recuperación de la cola ([análisis, §12](../requirements-analysis.md#12-reconciliación-de-exclusiones)).

## Breve descripción

Una programación es una ventana de descarga (días y horas) o un inicio único. Mientras la ventana está cerrada, `run` no envía jobs. Al cerrarse, deja terminar los jobs en curso o los detiene, según la política. La programación se guarda y sobrevive a los reinicios.

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User ejecuta `schedule set --window "lun-vie 23:00-06:00"`.
2. El sistema valida la ventana y la guarda con la zona horaria local.
3. Con `run` en ejecución, fuera de la ventana el sistema no envía jobs ([BR-37](../business-rules.md)) y lo avisa una vez, con la hora de apertura (BR-11).
4. Al abrirse la ventana, `run` envía jobs.
5. Al cerrarse, `run` deja de enviar jobs y deja terminar los que están en curso (como UC-14).

## Flujos alternativos

- **A1. Inicio único:** `[estado: ausente]` `schedule once 2026-12-01T02:00`. `run --keep-waiting` empieza a enviar jobs a esa hora.
- **A2. Arranque por un programador externo** `[estado: ausente]` (D-13: solo para arrancar sin `run` activo; no hay servicio residente): `schedule install` registra una tarea en el Programador de tareas de Windows que ejecuta `run` en la ventana. El sistema solo crea, consulta y borra su propia tarea.
- **A3. Consultar:** `[estado: ausente]` `schedule show` muestra la programación vigente y la siguiente apertura.
- **A4. Modificar o cancelar:** `[estado: ausente]` `schedule set` o `schedule clear`. `run`, si está en marcha, lo aplica en su siguiente ciclo.
- **A5. Ejecutar ahora:** `[estado: ausente]` `run --ignore-schedule` envía jobs fuera de la ventana para esa ejecución.
- **A6. Detener al cerrar la ventana:** `[estado: ausente]` con `--stop-at-window-end`, los jobs en curso se detienen como una interrupción (UC-05 A6) y continúan en la siguiente ventana.
- **A7. Reinicio del equipo:** `[estado: ausente]` la programación sigue vigente. Si un programador externo arranca `run`, se recupera la cola (UC-06).
- **A8. Cambio de hora (horario de verano):** `[estado: ausente]` la ventana usa la hora local vigente en cada momento.
- **A9. Conexión de uso medido** `[estado: ausente]` (prioridad baja): con `respect_metered_connection`, `run` no envía jobs mientras Windows marque la conexión como de uso medido, igual que una ventana cerrada (BR-37). Origen: Seal (no descargar con datos móviles); la exclusión «propia de Android» no se sostiene porque Windows también tiene conexiones de uso medido.

## Excepciones

- **E1. Ventana inválida** `[estado: ausente]` (formato, fin igual al inicio): código `2`.
- **E2. No se puede registrar la tarea externa** `[estado: ausente]` (permisos, política del equipo): se informa de la causa; la programación interna sigue vigente.

## Garantías

- **De éxito:** ningún job empieza fuera de la ventana salvo con `--ignore-schedule`.
- **Mínima:** la programación nunca cancela jobs ni borra parciales.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-10, BR-11 y BR-37.
- **Requisitos suplementarios:** SUP-U04 y SUP-R08 (si la ventana es de noche, el equipo no debe suspenderse con jobs en curso).
- **Restricciones:** el sistema solo administra la tarea externa que creó.
- **Dependencias:** UC-14 y UC-06; UC-11 y UC-17 (admisión común).

## Criterios de aceptación

1. Con un reloj falso, ningún job se envía fuera de la ventana.
2. La programación sobrevive a un reinicio de `run`.
3. Cerrar la ventana nunca cancela un job.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Ventanas, inicio único y cambio de hora con un reloj falso | Cualquier sistema |
| Registro de la tarea en el Programador de tareas (A2) | **Windows** |
