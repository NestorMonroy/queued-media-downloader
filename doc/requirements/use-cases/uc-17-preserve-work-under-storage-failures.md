# UC-17: Preservar el trabajo ante fallos de almacenamiento

- **Objetivo:** cuando el almacenamiento impide escribir (falta espacio, se excede la cuota, una carpeta no existe o no admite escritura, otro programa retiene un archivo), no se pierde nada de lo descargado, ningún archivo del User se borra para hacer sitio, los jobs que escriben en otras unidades siguen, y el User sabe qué condición es, en qué unidad o carpeta, y qué hacer.
- **Actor principal:** User
- **Actor secundario:** Sistema de archivos (unidades locales, extraíbles y de red; programas que retienen archivos, como antivirus y clientes de sincronización)
- **Disparador:**
  - **preventivo:** `run` va a enviar un job;
  - **reactivo:** una operación de archivo falla durante la descarga, la unión de ffmpeg, la extracción de audio o el movimiento del archivo final.
- **Relación:** extiende UC-03 (pasos 4 a 11) y UC-04 (paso 2). Comparte con UC-11 el aplazamiento sin gastar intentos ([BR-04](../business-rules.md)) y la política de continuidad (D-2). UC-01 A10 hace la misma comprobación preventiva en `diagnose`.
- **Prioridad:** media
- **Significativo para la arquitectura:** sí: control de admisión por unidad e identificación de la condición en toda la cadena de causas
- **Estado:** propuesto; **no implementado**. Hoy cada condición termina el job como `FAILED` con `FILESYSTEM`, `UNKNOWN` o `POSTPROCESSING` ([catálogo de condiciones, §3.2](../failure-conditions.md#32-cómo-llega-la-información-la-cadena-de-causas)). Decisiones D-5 y D-12 pendientes.
- **Origen:**
  - la evidencia de la cadena de causas de yt-dlp 2026.11.23 (catálogo, §3.2);
  - VoiceStudio y VoiceBlueprintPro: disco lleno por `errno` y `winerror` en toda la cadena, comprobación previa del destino, espacio de una carpeta que aún no existe, volumen no confiable;
  - la revisión del Responsable (2026-11-26): no todos los fallos de almacenamiento son iguales, y una comprobación previa no garantiza la descarga entera.
- **Historial:** el UC-13 retirado («esperar espacio en disco») solo trataba el disco lleno y se consolidó en UC-11 A3. Esta revisión muestra que el almacenamiento tiene condiciones de naturaleza distinta (espacio, cuota, permisos, disponibilidad, uso compartido), con prevención y reacción propias, y que no todas se resuelven esperando. Por eso vuelve a ser un caso de uso propio, con un identificador nuevo; el 13 no se reutiliza.

## Breve descripción

Antes de enviar un job, el sistema comprueba que su destino existe o se puede crear, que admite escritura y que su unidad tiene espacio para el tamaño estimado. Si una escritura falla después, identifica la condición en toda la cadena de causas y la trata según su naturaleza:
- espacio o cuota: aplaza los jobs de esa unidad;
- uso compartido: los reintentos de yt-dlp; si persiste, falla;
- permisos o configuración: falla, con la acción concreta;
- unidad ausente: aplaza los jobs de esa unidad (D-12).

## Precondiciones

- `run` está en ejecución.

## Flujo básico

1. `run` elige el siguiente job.
2. El sistema comprueba el destino del job ([BR-28](../business-rules.md)): la carpeta de descargas y la de parciales existen o se pueden crear, admiten escritura, y sus unidades tienen espacio libre por encima del tamaño estimado del job, si se conoce, más el margen configurado.
3. La comprobación pasa y el sistema envía el job.
4. El job escribe sus parciales, ffmpeg une o convierte, y el archivo final se mueve a su destino (UC-03, pasos 6 a 11).
5. El job termina `COMPLETED`.

## Flujos alternativos

**Preventivos** (paso 2):
- **A1. Espacio libre insuficiente para el tamaño estimado:** el sistema no envía el job ni los demás jobs de esa unidad mientras dure la condición ([BR-09](../business-rules.md)), sigue con los de otras unidades e informa una vez por unidad con el espacio libre y el estimado. El job sigue `PENDING`, sin gastar un intento.
- **A2. Tamaño desconocido:** yt-dlp no siempre da `filesize` ni `filesize_approx`. El sistema solo exige el margen configurado y confía en la reacción (A4).
- **A3. La carpeta no existe y no se puede crear, o no admite escritura:** el sistema distingue la causa:
  - **configuración:** la carpeta configurada es inválida. Se informa de la clave (`download_directory`, `state_directory`), y los jobs no se envían hasta que se corrija y se ejecute `run` de nuevo;
  - **unidad ausente:** la unidad extraíble o de red no está. Se aplazan los jobs de esa unidad (D-12);
  - **permisos o restricciones:** ACL, solo lectura, acceso controlado a carpetas, volumen no confiable. Se informa de la carpeta y de la restricción.

**Reactivos** (paso 4); la comprobación del paso 2 pasó, pero la condición apareció después:
- **A4. Espacio insuficiente durante la descarga o la unión** (`ENOSPC`, `winerror` 112 o 39, texto de ffmpeg): el job se aplaza sin gastar un intento y conserva sus parciales ([BR-04](../business-rules.md)). Se dejan de enviar los jobs de esa unidad, como A1. Los videos y audios ya descargados para una unión se conservan; al continuar, solo se repite la unión.
- **A5. Cuota excedida** (`EDQUOT`, `winerror` 1295): como A4, con un mensaje que dice que es la cuota del usuario.
- **A6. Uso compartido o bloqueo** (`winerror` 32 o 33): yt-dlp reintenta (`file_access_retries`, [BR-26](../business-rules.md)). Si persiste, el job falla `FILESYSTEM` con un mensaje que nombra el archivo y sugiere cerrarlo o excluir la carpeta del antivirus o de la sincronización.
- **A7. Acceso denegado** (`winerror` 5 o `EACCES` sin 32 ni 33): el job falla `FILESYSTEM` sin aplazarse. El mensaje nombra la ruta y la operación (crear la carpeta, abrir el parcial, mover el archivo final) y dice que reintentar sin cambiar nada no sirve.
- **A8. La unidad desaparece a mitad del job** (extraíble retirada, recurso de red caído): como A3 con la unidad ausente.
- **A9. La condición desaparece:** se libera espacio, se amplía la cuota o vuelve la unidad. Los jobs aplazados continúan desde sus parciales, en la misma ejecución o en otra, según la política de continuidad (D-2).
- **A10. La condición no se puede identificar:** yt-dlp perdió la causa y el texto no coincide con ninguna condición conocida. El job falla con el mensaje original y el motivo más cercano (`FILESYSTEM` o `UNKNOWN`); el log guarda la cadena completa para el informe de diagnóstico (UC-16).

## Excepciones

- **E1. Se llena la unidad del estado** (base de datos o log): `run` no puede guardar ni el aplazamiento. Termina con código `1` y nombra la unidad; los jobs quedan `RUNNING` y se recuperan en el siguiente `run` (UC-06).
- **E2. Todas las unidades de destino tienen una condición que aplaza:** se aplica la política de continuidad (D-2), como en UC-11 paso 5.

## Garantías

- **De éxito:** el job terminó, o quedó aplazado sin gastar intentos hasta que la condición desapareció; los jobs de otras unidades siguieron.
- **Mínima:**
  - el sistema nunca borra ni mueve archivos del User para liberar espacio;
  - los parciales y la reclamación del nombre final se conservan;
  - un job nunca queda `COMPLETED` sin su archivo final (UC-03 A8);
  - el mensaje siempre nombra la unidad o la carpeta afectada.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-04, BR-08, BR-09, BR-17, BR-25, BR-26, BR-27 y BR-28.
- **Requisitos suplementarios:** SUP-R09, SUP-U05, SUP-P07 y SUP-V03.
- **Restricciones:**
  - una comprobación previa nunca se trata como garantía: la reacción (A4 a A8) es siempre necesaria;
  - no se fija un espacio mínimo universal: el margen y la estimación dependen de SUP-P07 y de D-5.
- **Dependencias:** UC-03, UC-04, UC-06 y UC-11 (aplazamiento y política); UC-01 A10 (misma comprobación en `diagnose`).

## Criterios de aceptación

1. Cada condición del [catálogo, §3.1](../failure-conditions.md#31-condiciones) se identifica por su código en cualquier punto de la cadena de causas (`exc_info`, `__cause__`, `__context__`) o por su texto, en los cinco caminos del §3.2.
2. El espacio insuficiente y la cuota excedida nunca dejan un job `FAILED` ni incrementan su `attempt_count`, también cuando aparecen tras una comprobación previa correcta.
3. El acceso denegado y la configuración inválida no se aplazan: fallan con un mensaje que nombra la ruta y la acción.
4. Con una unidad sin espacio, los jobs que escriben en otra unidad se completan.
5. Ningún archivo fuera de las carpetas de parciales del job cambia (tamaño, fecha y SHA-256).

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Identificación de cada condición con excepciones reales de yt-dlp en los cinco caminos del §3.2 y textos reales de ffmpeg | Cualquier sistema |
| A1 a A3 con comprobadores falsos (espacio, existencia, escritura) y un pool guionizado | Cualquier sistema |
| A4 con una unidad pequeña real a mitad de una descarga y de una unión | Linux (sistema de archivos en memoria con tamaño fijo) y **Windows** (unidad virtual pequeña), campaña |
| A5 con una cuota real | **Windows** o Linux con cuotas, si el entorno lo permite; si no, solo con excepciones simuladas |
| Traducción de `winerror` 5, 32, 33, 39, 112 y 1295 a `errno` | **Windows**, prueba `windows` |
| A6 con un archivo abierto por otro proceso sin compartir | **Windows** |
| A8 con una unidad extraíble retirada | **Windows**, manual, solo si el Evaluador lo considera seguro |
