# UC-11: Preservar los jobs ante condiciones externas

- **Objetivo:** cuando algo ajeno al contenido impide descargar (el sitio restringe el acceso, el equipo pierde la conexión o falta espacio), ningún job sano se pierde, no se gastan sus intentos, no se insiste ante quien está restringiendo, y el User sabe qué pasa y qué hará la cola.
- **Actor principal:** User
- **Actor secundario:** Media site
- **Disparador:** suceso externo durante `run`, reconocido por una regla definicional: restricción del sitio ([BR-01](../business-rules.md)), corte de conectividad ([BR-05](../business-rules.md)) o almacenamiento insuficiente ([BR-08](../business-rules.md)).
- **Relación:** extiende UC-03 (pasos 4 a 11) y UC-04 (paso 2). UC-03 funciona sin esta extensión: hoy cada job afectado falla con su motivo (UC-03 A2).
- **Prioridad:** alta
- **Significativo para la arquitectura:** sí (nuevo job event, control de admisión en la planificación de `run`)
- **Estado:** propuesto; **no implementado**. La política de continuidad está **pendiente de decisión** (D-2, D-4 y D-5 del [análisis de requisitos](../requirements-analysis.md#9-decisiones-pendientes)).
- **Origen:** campaña T42 (corte de red en el paso 5.2; bloqueo antibots desde el paso 5.7) y las referencias del [análisis, §6](../requirements-analysis.md#6-hallazgos-de-las-referencias-y-su-incorporación).
- **Historial:** consolida los antiguos UC-11 (bloqueo del sitio), UC-12 (red) y UC-13 (disco), propuestos y retirados el 2026-11-26. Los tres seguían el mismo flujo: reconocer, aplazar, no insistir, informar y continuar. Solo diferían en la regla que los reconoce y en su alcance, que aquí son escenarios.

## Breve descripción

Una condición externa no es un fallo del contenido. El sistema la reconoce, aplaza los jobs afectados sin gastar intentos, deja de enviar los que no pueden avanzar, informa al User y continúa según la política de continuidad que se decida.

Cada condición tiene su alcance ([catálogo de condiciones de fallo](../failure-conditions.md)):
- **Restricción del sitio:** solo los jobs de ese sitio.
- **Corte de conectividad:** todos los jobs.
- **Falta de espacio:** los jobs que escriben en la unidad llena.

## Precondiciones

- `run` está en ejecución.

## Flujo básico

1. Un job encuentra una condición externa ([BR-01](../business-rules.md), [BR-05](../business-rules.md) o [BR-08](../business-rules.md)), después de agotar los reintentos propios de yt-dlp ([BR-07](../business-rules.md)).
2. El sistema aplaza el job ([BR-04](../business-rules.md)): vuelve a la cola sin gastar un intento y conserva sus parciales y la reclamación de su nombre.
3. El sistema deja de enviar los jobs afectados por la condición ([BR-03](../business-rules.md)); los demás continúan (continuidad selectiva).
4. El sistema informa al User de la condición, su alcance, los jobs aplazados y lo que hará la cola ([BR-11](../business-rules.md)).
5. El sistema aplica la política de continuidad (decisión D-2): esperar y comprobar, o terminar de forma ordenada cuando solo queden jobs aplazados.
6. Cuando la condición desaparece, en esta ejecución o en un `run` posterior, los jobs aplazados continúan desde lo ya descargado (UC-06).

## Flujos alternativos

- **A1. Restricción del sitio** (paso 1): comprobación antibots, captcha o límite de peticiones (BR-01). Solo se dejan de enviar los jobs de ese sitio, y el sitio no recibe más peticiones hasta que la política lo permita (BR-03). El ritmo de peticiones por sitio ([BR-02](../business-rules.md)) es la prevención previa.
- **A2. Corte de conectividad** (paso 1): no se resuelve el nombre, se rechaza la conexión o la red no es alcanzable (BR-05). Se dejan de enviar todos los jobs. La conectividad se comprueba sin hacer peticiones HTTP al sitio ([BR-06](../business-rules.md)). Al despertar de una suspensión, la conexión puede tardar unos segundos en volver (SUP-R08).
- **A3. Almacenamiento insuficiente** (paso 1): una escritura falla por falta de espacio, o el espacio libre no basta para el job antes de enviarlo (BR-08). Se dejan de enviar los jobs que escriben en esa unidad. El sistema nunca libera espacio por su cuenta. Los videos y audios ya descargados para una unión se conservan.
- **A4. Varios jobs encuentran la condición a la vez** (paso 1): cada job se aplaza; el aviso es uno por condición.
- **A5. La condición llega durante la expansión de una playlist:** la expansión se aplaza. Las entradas ya creadas se conservan y, al continuar, se encuentran como duplicadas (UC-04 A2).
- **A6. La condición llega a mitad de una descarga o de una unión:** como el paso 2. La descarga continúa desde sus parciales y la unión se repite.
- **A7. `run` termina o se cierra con jobs aplazados:** siguen `PENDING`. Si la restricción de un sitio tiene un plazo guardado, el siguiente `run` lo respeta (UC-06 A10).
- **A8. El User cancela un job aplazado:** como UC-05 A1.
- **A9. El User quiere continuar antes de tiempo** (solo si D-2 elige esperar): `run --ignore-site-waits` descarta los plazos guardados.

## Excepciones

- **E1. La respuesta no se reconoce como condición externa:** el job sigue UC-03 A2 y falla con su motivo. Si una actualización de yt-dlp cambia los textos, las pruebas de contrato de BR-01 lo detectan (SUP-S01).
- **E2. El contenido pide una cuenta por sí mismo** (privado, con restricción de edad, solo para miembros): no es una restricción del sitio (BR-01) y falla con `UNAVAILABLE`.
- **E3. Se llena la unidad del estado y no se puede guardar ni el aplazamiento:** `run` termina con código `1` y nombra la unidad. Los jobs quedan `RUNNING` y se recuperan en el siguiente `run` (UC-06).
- **E4. Configuración no válida:** `run` informa de la clave y del valor y termina con código `2` sin enviar jobs.

## Garantías

- **De éxito:** ningún job quedó `FAILED` ni gastó un intento por la condición; los jobs no afectados continuaron; los afectados continuaron cuando la condición desapareció.
- **Mínima** (también si `run` termina o se cierra):
  - ningún job quedó `FAILED` por la condición;
  - se conservan los parciales, las reclamaciones y los archivos ya descargados;
  - el sitio restringido no recibió más peticiones que las que permite BR-03.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-01 a BR-08, BR-11 y BR-12.
- **Requisitos suplementarios:** SUP-R06, SUP-R07, SUP-R09, SUP-R11, SUP-U04 y SUP-P05.
- **Restricciones:**
  - sin PO Tokens; cookies y cuentas, según D-1 (BR-12);
  - ningún mecanismo para evadir los controles de un sitio.
- **Dependencias:** UC-03, UC-04, UC-05 y UC-06; diseño propuesto en [ADR-0031](../../notes/adr-0031-site-waits-and-network-waits.md).

## Criterios de aceptación

1. Una restricción del sitio, un corte de conectividad o un disco lleno nunca dejan un job `FAILED` ni incrementan su `attempt_count`.
2. Durante la restricción de un sitio, los jobs de otros sitios se completan.
3. Mientras dura una restricción, el sitio no recibe peticiones salvo las que la política permite.
4. El User recibe un aviso por condición, con su alcance y lo que hará la cola.
5. Tras la condición, cada job aplazado continúa desde sus parciales, sin volver a descargar lo ya descargado.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| BR-01 con el código real de yt-dlp: las tres respuestas de restricción frente a un contenido que pide una cuenta, con los dos apóstrofos | Cualquier sistema |
| BR-05 y BR-08 con excepciones reales: `errno` y `winerror` en toda la cadena de causas | Cualquier sistema |
| Pasos 1 a 6 y A1 a A7, con un pool guionizado, un reloj falso y comprobadores falsos | Cualquier sistema |
| Corte real contra el servidor local (se detiene y se vuelve a arrancar) | Cualquier sistema |
| Disco lleno real (unidad pequeña) y corte de red real | **Windows**, campaña (VUC-04, VUC-05) |
| Restricción real de YouTube | **Windows**, solo si ocurre; no se provoca a propósito |
