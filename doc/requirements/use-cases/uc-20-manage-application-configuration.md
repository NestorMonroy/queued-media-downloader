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
- **Propuestas pendientes de aprobación (2.5.0):** A8, A9 y A10, marcadas como propuestas; [análisis de requisitos, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
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
- **A8. Modo privado** `[estado: ausente; propuesto]` (paso 1): con el modo privado activo, los jobs que terminan no dejan historial terminado, búsquedas ni logs de actividad por job. Se conserva solo lo necesario para recuperar los jobs no terminados y se elimina cuando terminan ([BR-49](../business-rules.md), D-21). El modo puede activarse para toda la aplicación o para un job concreto al encolarlo. Evidencia: YTDLnis (`incognito`: ni historial ni log del job), Seal (`privateMode`: sin historial) y Parabolic («Exclude from History» por descarga); [análisis, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
- **A9. Borrar datos de la aplicación por categoría** `[estado: ausente; propuesto]` (paso 1): el User elige qué borrar: caché de metadatos, temporales huérfanos, historial terminado, historial de búsqueda o credenciales. Cada categoría se borra por separado, nunca los resultados ni los jobs no terminados, y el sistema informa del espacio liberado. Evidencia: NewPipe y GreenTuber (borrado de caché e historiales) y YTDLnis (`cleanup_leftover_downloads`, `temporary_files`).
- **A10. Disparador de emergencia** `[estado: ausente; propuesto]` (Android): otra aplicación envía el disparador de pánico; el sistema cierra la interfaz y, si el User lo configuró, aplica el borrado de A9. Evidencia: NewPipe y GreenTuber (`PanicResponderActivity` con `info.guardianproject.panic.action.TRIGGER`); en NewPipe solo cierra y retira la tarea, y el borrado figura como pendiente en su código.

## Excepciones

- **E1. Valor o clave inválidos:** `[estado: ausente]` el sistema nombra la clave y el valor, no escribe nada y termina con código `2`.
- **E2. `config.toml` ilegible:** `[estado: ausente]` `config show` lo informa con la causa y muestra el resto.

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
