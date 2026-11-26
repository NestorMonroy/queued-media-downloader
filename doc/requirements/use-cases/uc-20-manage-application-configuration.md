# UC-20: Administrar la configuración

- **Objetivo:** el User sabe qué configuración está vigente y de dónde sale cada valor; la cambia y la valida sin editar archivos a ciegas, y puede llevarla a otro equipo.
- **Actor principal:** User
- **Actor secundario:** Programa cliente
- **Disparador:** el programa no se comporta como el User espera, o el User quiere cambiar una preferencia permanente.
- **Relación:** UC-01 valida la configuración al verificar el entorno (A6); UC-18 guarda los perfiles en ella; UC-19 guarda las referencias de acceso, nunca los secretos.
- **Prioridad:** media
- **Significativo para la arquitectura:** no; reutiliza `configuration` y la precedencia existente (SUP-F03)
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: parcial (la carga con precedencia y la validación existen; la consulta, la modificación y el traslado no).
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Ampliaciones aceptadas (instrucción 2.6.0):** A8, A9 y A10, propuestas en la 2.5.0; [análisis de requisitos, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
- **Origen:**
  - **Seal y YTDownload-2026:** pantallas de ajustes.
  - **Kannagi:** `config.yaml` y preajustes.
  - **Producto:** la precedencia existente: argumentos, variables de entorno, `config.toml`, valores por defecto.

## Breve descripción

`config show` muestra la configuración efectiva y, por cada clave, su origen. `config set`, `config unset` y `config reset` modifican `config.toml` con validación. `config check` valida sin ejecutar nada. `config export` y `config import` trasladan la configuración sin credenciales.

Se distinguen cuatro tipos de información:
- **configuración:** permanente, en `config.toml`;
- **credenciales:** solo referencias (UC-19);
- **datos persistidos:** la cola, en SQLite;
- **estado operativo:** pausa, aplazamientos, programación vigente.

## Precondiciones

- Ninguna: debe funcionar aunque la configuración sea inválida.

## Flujo básico

1. El User ejecuta `config show`.
2. El sistema resuelve la configuración con la precedencia vigente (SUP-F03).
3. El sistema muestra cada clave con su valor efectivo y su origen (argumento, variable de entorno, `config.toml` o valor por defecto) y oculta los valores sensibles (SUP-SEC01).

## Flujos alternativos

- **A1. Modificar:** `[estado: ausente]` `config set CLAVE VALOR` valida el valor y lo escribe en `config.toml`, conservando los comentarios del archivo. Si una variable de entorno lo sustituye, el sistema avisa de que el cambio no tendrá efecto.
- **A2. Quitar y restablecer:** `[estado: ausente]` `config unset CLAVE` vuelve al valor por defecto de esa clave; `config reset` crea una copia de `config.toml` y lo deja vacío, con confirmación.
- **A3. Validar:** `[estado: ausente]` `config check` informa de cada clave inválida y de las combinaciones incompatibles (por ejemplo, un perfil predeterminado inexistente).
- **A4. Salida para otros programas:** `[estado: ausente]` `--json`, como UC-08 A5.
- **A5. Exportar e importar:** `[estado: ausente]` `config export ARCHIVO` incluye los perfiles (UC-18) y las referencias de acceso sin secretos. `config import` valida antes de escribir, muestra las diferencias y pide confirmación.
- **A6. Cambio durante `run`:** `[estado: ausente]` `run` lee la configuración al arrancar. Un cambio se aplica en el siguiente `run`, y el sistema lo avisa.
- **A7. Preferencias de red** `[estado: ausente]` (prioridad baja): `force_ipv4` para redes con IPv6 roto (`source_address` de yt-dlp). Cambiar el agente de usuario queda excluido: no resuelve una necesidad del User y puede servir para evadir controles (BR-12).
- **A8. Modo privado** `[estado: ausente]` (paso 1): el User activa el modo privado para toda la aplicación o para un job al encolarlo; desde ese momento se aplica el contrato del modo privado de esta especificación ([BR-49](../business-rules.md), D-21). Evidencia: YTDLnis (`incognito`), Seal (`privateMode`) y Parabolic («Exclude from History»); [análisis, §15](../requirements-analysis.md#15-descubrimiento-funcional-250) y [§17.6](../requirements-analysis.md#176-privacidad-br-49-y-sup-d03).
- **A9. Borrar datos de la aplicación por categoría** `[estado: ausente]` (paso 1): el User elige qué borrar: caché de metadatos, temporales huérfanos, historial terminado, historial de búsqueda o credenciales. Cada categoría se borra por separado, nunca los resultados ni los jobs no terminados, y el sistema informa del espacio liberado. Evidencia: NewPipe y GreenTuber (borrado de caché e historiales) y YTDLnis (`cleanup_leftover_downloads`, `temporary_files`).
- **A10. Disparador de emergencia** `[estado: ausente]` (Android): otra aplicación envía el disparador de pánico; el sistema cierra la interfaz y, si el User lo configuró, aplica el borrado de A9. Evidencia: NewPipe y GreenTuber (`PanicResponderActivity` con `info.guardianproject.panic.action.TRIGGER`); en NewPipe solo cierra y retira la tarea, y el borrado figura como pendiente en su código.

## Excepciones

- **E1. Valor o clave inválidos:** `[estado: ausente]` el sistema nombra la clave y el valor, no escribe nada y termina con código `2`.
- **E2. `config.toml` ilegible:** `[estado: ausente]` `config show` lo informa con la causa y muestra el resto.

## Contrato del modo privado (A8)

| Aspecto | Comportamiento |
|---|---|
| Activación | Global (configuración) o por job (al encolarlo). Un job queda privado si se encoló en modo privado; desactivar el modo global no cambia los jobs ya encolados. |
| Operaciones afectadas | Las que crean o actualizan jobs privados: encolar, ejecutar, reintentar, cancelar, terminar y purgar. |
| Qué deja de conservarse | La fila del job en el historial terminado y sus metadatos de resultado (URL, título, identificadores de medio, ruta) cuando el job termina; las líneas de log con su URL, título o rutas, que pasan a llevar solo el identificador del job y la condición técnica. |
| Qué se elimina y cuándo | Al llegar el job a un estado terminado: su fila y sus sucesos en el almacén de jobs, y sus datos de recuperación (parciales, marca de propiedad), como en cualquier job. |
| Jobs pendientes y activos | Se conservan con todos sus datos mientras no terminan, porque la recuperación (D-9) los necesita; la lista los muestra igual que a los demás. |
| Outputs publicados | Son archivos del User: no se ocultan, no se cifran ni se borran. La reclamación del output se libera al eliminar el registro del job; desde entonces el archivo es un archivo externo para el producto. |
| Reinicio | Un job privado no terminado se recupera como cualquier otro y conserva su marca privada. |
| Salir del modo privado | No cambia los jobs ya encolados ni restaura lo que ya se eliminó. |
| Credenciales | Sin cambios (SUP-SEC01). |

**Datos que se conservan mientras el job privado no termina:**

| Dato | Operación que lo usa | Finalidad | Requisito | Ciclo de vida | En modo privado |
|---|---|---|---|---|---|
| Registro del job (URL operativa, especificación, destino, estado) | UC-03, UC-06, UC-14 | Ejecutar y recuperar | D-9, SUP-D02 | Vida del job | Se elimina al terminar |
| Marca de propiedad de los parciales | UC-06, UC-10 | No tocar archivos ajenos | ADR-0030 | Hasta terminar | Se elimina al terminar |
| Reclamación del output | UC-03, UC-25 | Propiedad del output | ADR-0033 | Hasta eliminar el registro | Se libera al terminar |
| Líneas de log | UC-16 | Diagnóstico | SUP-SEC07 | Rotación habitual | Sin URL, título ni rutas |

No se añade ninguna categoría de datos para el modo privado.

## Garantías

- **De éxito:** la configuración queda válida y su origen es visible.
- **Mínima:** un cambio inválido nunca se escribe; las opciones de los jobs ya encolados no cambian (BR-33).

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-33 y BR-34.
- **Requisitos suplementarios:** SUP-F03, SUP-U01, SUP-SEC01 y SUP-I01.
- **Restricciones:** sin credenciales en `config.toml`; solo referencias.
- **Dependencias:** UC-01, UC-18 y UC-19.

## Criterios de aceptación

1. Para cada clave, el origen mostrado coincide con la precedencia SUP-F03.
2. Ningún valor sensible aparece en `config show` ni en `config export`.
3. Una importación inválida no cambia nada.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Origen de cada clave con argumentos, variables, archivo y valores por defecto | Cualquier sistema |
| Escritura que conserva los comentarios; importación con diferencias | Cualquier sistema |
