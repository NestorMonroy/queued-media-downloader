# UC-13: Esperar a que haya espacio en disco

- **Objetivo:** si se llena el disco de las descargas o del estado, la cola no se pierde: los contenidos esperan y continúan cuando el User libera espacio.
- **Actor principal:** User
- **Disparador:** suceso externo durante `run`: una escritura falla por falta de espacio, o el espacio libre baja del mínimo antes de enviar un job (regla [BR-08](../business-rules.md)).
- **Relación:** extiende UC-03 (pasos 6 a 11) y UC-04 (paso 4).
- **Prioridad:** media
- **Significativo para la arquitectura:** no (reutiliza el aplazamiento y la espera de UC-12)
- **Estado:** propuesto; decisión D-5 pendiente ([análisis](../unattended-operation-analysis.md))
- **Diseño propuesto:** [ADR-0031](../../notes/adr-0031-site-waits-and-network-waits.md)

## Breve descripción

Una playlist grande puede llenar el disco. Hoy cada job falla con `FILESYSTEM` uno tras otro, con el mismo patrón que un corte de red. Con este caso de uso, `run` aplaza el job afectado, deja de enviar jobs, avisa de qué unidad está llena y cuánto espacio falta, y continúa cuando hay espacio.

## Precondiciones

- `run` está en ejecución.

## Flujo básico

1. Antes de enviar un job, o al escribir durante una descarga o una unión, el sistema detecta el disco lleno ([BR-08](../business-rules.md)).
2. El sistema aplaza el job afectado, si lo hay ([BR-04](../business-rules.md)), deja de enviar jobs y avisa al User de la unidad, el espacio libre y el mínimo; por ejemplo, `Not enough free space on D: (300 MiB free, 1024 MiB needed); waiting`. Ver [BR-11](../business-rules.md).
3. El sistema comprueba el espacio libre cada cierto tiempo ([BR-09](../business-rules.md)).
4. El User libera espacio.
5. El sistema avisa (`Enough free space on D:; continuing`) y vuelve a enviar jobs. La descarga aplazada continúa desde lo ya descargado (UC-06).

## Flujos alternativos

- **A1. Se llena la unidad del estado** (la de la base de datos y los logs): igual que el flujo básico. Si ni siquiera se puede guardar el aplazamiento, `run` termina con código `1` y un mensaje que nombra la unidad; los jobs en curso quedan `RUNNING` y se recuperan en el siguiente `run` (UC-06).
- **A2. El espacio no se libera:** `run` sigue esperando y repite el aviso; `Ctrl+C` lo termina con código `130` y los jobs siguen pendientes.
- **A3. La unión con ffmpeg falla por falta de espacio:** como el flujo básico. Los archivos de video y audio ya descargados se conservan y la unión se repite al continuar.
- **A4. El User cancela un job que espera:** como UC-05 A1.

## Excepciones

- **E1. Otro error del sistema de archivos** (permiso denegado, ruta no válida): no es disco lleno; el job sigue UC-03 A2 y falla con `FILESYSTEM`.

## Garantías

- **De éxito:** ningún job quedó fallido por falta de espacio; la cola continuó cuando hubo espacio.
- **Mínima:** ningún archivo final ni parcial se borró para hacer espacio; el sistema nunca borra archivos del User.

## Requisitos especiales

- El sistema no libera espacio por su cuenta.

## Configuración

`min_free_disk_mib` ([BR-08](../business-rules.md)) y `disk_check_seconds` ([BR-09](../business-rules.md)).

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| BR-08: `ENOSPC` de Python y de ffmpeg frente a otros errores del sistema de archivos | Cualquier sistema |
| Pasos 1 a 5 y A2 con un medidor de espacio falso y un reloj falso | Cualquier sistema |
| Disco lleno real (unidad pequeña: un VHD de 1 GiB) | **Windows**, campaña |
