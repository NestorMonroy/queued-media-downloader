# UC-19: Administrar perfiles de acceso autorizado

- **Objetivo:** el User configura, una vez, el acceso legítimo que necesita para ciertos sitios (un archivo de cookies que él proporciona, un proxy con o sin credenciales) y lo reutiliza en sus descargas. Sus credenciales nunca se exponen, se copian a la cola ni se mezclan entre sitios.
- **Actor principal:** User
- **Actores secundarios:** Media site; Proxy
- **Disparador:**
  - un contenido que el User tiene derecho a ver pide iniciar sesión (privado, con restricción de edad, solo para miembros);
  - o la red del User solo permite salir por un proxy.
- **Relación:** UC-02 A12 y UC-18 lo referencian; UC-01 A11 lo diagnostica; UC-03 lo usa al descargar.
- **Prioridad:** media
- **Significativo para la arquitectura:** sí: ciclo de vida de credenciales, aislamiento por worker y limpieza tras un cierre
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: ausente. Condiciones técnicas: D-1 y D-7; la lectura de cookies del navegador (A10) queda condicionada.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:**
  - análisis del acceso, [§7.4](../requirements-analysis.md#74-acceso-proxy-y-cookies-en-una-cola-persistente);
  - VoiceStudio y VoiceBlueprintPro: `cookies.txt` efímero;
  - Seal: perfiles de cookies;
  - Kannagi: modos de cookies;
  - YTDownload-2026: proxy y cuenta técnica;
  - yt-dlp: `cookiefile`, `proxy`.

## Breve descripción

Un perfil de acceso tiene un nombre, los sitios a los que se aplica y una referencia a sus credenciales: la ruta de un archivo de cookies del User, o un proxy con credenciales tomadas del almacén de credenciales de Windows. El perfil guarda la referencia, nunca el secreto. Al descargar, el sistema usa una copia temporal por job, restringida al usuario y borrada al terminar. Leer las cookies del navegador queda como alternativa de D-1; no es el flujo básico porque en Windows no es fiable con Chrome ni Edge.

## Precondiciones

- UC-01 completado. D-1 o D-7 resueltas a favor del tipo de acceso usado.

## Flujo básico

1. El User ejecuta `access add NOMBRE --site youtube --cookies RUTA`.
2. El sistema valida el archivo: formato Netscape, tamaño razonable y cookies del sitio indicado. Nunca muestra su contenido.
3. El sistema guarda el perfil con la referencia al archivo y los sitios. No copia las cookies a la configuración ni a la base de datos ([BR-34](../business-rules.md)).
4. Al enviar un job de ese sitio, el sistema hace una copia temporal de las cookies para ese job ([BR-35](../business-rules.md)) y se la pasa a yt-dlp.
5. Al terminar el job, con cualquier resultado, el sistema borra la copia. El archivo original no cambia.

## Flujos alternativos

- **A1. Proxy:** `[estado: ausente]` `access add NOMBRE --proxy URL [--credential NOMBRE_EN_EL_ALMACÉN]`. La URL se guarda sin contraseña; la contraseña se lee del almacén de credenciales de Windows al usarla.
- **A2. Consultar:** `[estado: ausente]` `access list` y `access show NOMBRE` muestran el nombre, los sitios, el tipo, la ruta y la fecha de la última validación, nunca el secreto.
- **A3. Validar:** `[estado: ausente]` `access check NOMBRE` comprueba el archivo y su caducidad declarada, sin peticiones al sitio. Las cookies caducadas se informan.
- **A4. Actualizar:** `[estado: ausente]` el User reemplaza el archivo o cambia la ruta. Los jobs pendientes usan la versión vigente al enviarse: el job guarda el nombre del perfil, no las cookies.
- **A5. Eliminar:** `[estado: ausente]` `access delete NOMBRE`. Los jobs pendientes que lo usan fallan al enviarse con un mensaje que lo nombra, sin aplazarse.
- **A6. Sesión caducada al descargar:** `[estado: ausente]` el sitio vuelve a pedir que se inicie sesión. El job falla `UNAVAILABLE` con la indicación de renovar el archivo; no se reintenta con otras credenciales.
- **A7. Varios workers del mismo sitio:** `[estado: ausente]` cada job tiene su propia copia. yt-dlp reescribe su copia al cerrar sin afectar a las demás ni al original.
- **A8. Cierre inesperado:** `[estado: ausente]` las copias temporales que queden se borran al arrancar `run` (UC-06), antes de enviar ningún job.
- **A9. Cancelación:** `[estado: ausente]` como el paso 5.
- **A10. Cookies del navegador** `[estado: ausente; condicionado]` (condición técnica de D-1: las cookies `v20` de Chrome y Edge no se descifran en Windows; requiere evidencia en Windows): el perfil indica el navegador y el perfil del navegador. El sistema informa de las limitaciones conocidas en Windows.

## Excepciones

- **E1. Archivo inexistente, ilegible o en un formato no válido:** `[estado: ausente]` no se guarda; código `2`.
- **E2. Contenido para el que el User no tiene autorización:** `[estado: ausente]` el sitio lo rechaza aunque haya cookies. El job falla con `UNAVAILABLE`; el sistema nunca intenta otro mecanismo.
- **E3. No se puede crear la copia temporal restringida:** `[estado: ausente]` el job falla `FILESYSTEM` sin pasar las cookies a yt-dlp.

## Garantías

- **De éxito:** el job descargó con el acceso del perfil.
- **Mínima:**
  - ningún secreto aparece en el log, `diagnose`, el informe (UC-16), una exportación (UC-22) o un respaldo (UC-23) (SUP-SEC01);
  - la copia temporal nunca sobrevive al job ni a un arranque.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-12, BR-34 y BR-35.
- **Requisitos suplementarios:** SUP-SEC01, SUP-SEC03 y SUP-SEC04.
- **Restricciones:**
  - nunca para evadir una restricción del sitio (BR-12);
  - sin navegador automatizado ni administración de cuentas;
  - sin rotación de proxies.
- **Dependencias:** UC-01 A11, UC-02 A12, UC-06 y UC-18.

## Criterios de aceptación

1. Con valores trampa, ningún secreto aparece en ninguna salida ni en la base de datos.
2. Con dos workers del mismo sitio, el archivo original de cookies no cambia (SHA-256).
3. Tras un cierre a mitad de un job, no queda ninguna copia temporal después del siguiente arranque.
4. Las cookies de un sitio nunca se pasan a un job de otro sitio.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Ciclo de vida, validación, copias por job y limpieza tras un cierre | Cualquier sistema |
| Concurrencia: dos workers con el mismo perfil | Cualquier sistema |
| Almacén de credenciales de Windows y permisos de la copia (ACL) | **Windows** |
