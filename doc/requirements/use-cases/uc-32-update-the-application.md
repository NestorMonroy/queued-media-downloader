# UC-32: Actualizar la aplicación

- **Objetivo:** el User sabe si hay una versión nueva del producto en su canal de distribución y pasa a ella sin perder jobs, resultados, configuración ni perfiles.
- **Actor principal:** User
- **Disparador:** el User pide comprobar actualizaciones, o la comprobación periódica activada detecta una versión nueva.
- **Prioridad:** media.
- **Significativo para la arquitectura:** sí: depende del canal de distribución y encadena la migración del esquema y la recuperación (SUP-C10).
- **Estado:** candidato (propuesta de la instrucción 2.5.0, pendiente de aprobación del Responsable). Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** NewPipe (`NewVersionWorker`: comprueba un JSON publicado solo si la instalación es la del canal propio, avisa y abre la página del paquete; no instala), Open Video Downloader (`updater_check`, `updater_download`, `updater_install`), YTDLnis (`UpdateCheckWorker`), VidBee (`:upgrade` de su CLI en `d483045`: consulta el registro, guarda el resultado 30 días y no instala) y GreenTuber (aviso de actualización); evidencia y nivel en el [análisis de requisitos, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
- **Independencia:** UC-27 cambia las dependencias multimedia (yt-dlp, yt-dlp-ejs, deno, ffmpeg) dentro de la misma versión del producto. Aquí cambia el producto (motor, interfaces, contratos públicos y esquema), con migración y vuelta atrás propias.

## Breve descripción

El sistema consulta la versión publicada en el canal por el que se instaló. Si hay una nueva, informa de la versión, de sus cambios y de si es compatible con la instalación. La instalación la hace el canal (tienda o gestor de paquetes) o el procedimiento de la distribución directa; el producto nunca instala desde un canal distinto del suyo ([BR-51](../business-rules.md)). Tras la instalación, el primer arranque migra el esquema y conserva el estado (SUP-C10).

## Precondiciones

- Instalación con un canal identificado.

## Flujo básico

1. El User pide comprobar actualizaciones.
2. El sistema identifica el canal de la instalación y consulta la versión publicada en él.
3. El sistema informa de la versión instalada, de la publicada y de sus notas.
4. El User inicia la actualización con el mecanismo del canal.
5. Tras instalarla, el primer arranque migra el esquema (UC-01 A8) y conserva jobs, resultados, configuración y perfiles.

## Flujos alternativos

- **A1. Comprobación periódica** `[estado: ausente]` (paso 1): activada en la configuración; si hay versión nueva, avisa (UC-28) y no instala nada.
- **A2. Canal gestionado por una tienda** `[estado: ausente]` (paso 4): la tienda instala; el producto, si el canal lo permite, solo enlaza con ella.
- **A3. Distribución directa** `[estado: ausente]` (paso 4): el procedimiento documentado de la distribución (hoy, `git pull` y `uv sync`, ADR-0003) instala la versión; si el canal ofrece paquetes, se verifica su firma o su hash antes de instalar.
- **A4. Jobs en curso** `[estado: ausente]` (paso 4): la actualización espera a que `run` termine o la pospone, como las dependencias (BR-44).
- **A5. Sin versión nueva** `[estado: ausente]` (paso 3): el sistema lo informa.

## Excepciones

- **E1. Sin conexión o canal inaccesible** `[estado: ausente]` (paso 2): el sistema lo informa sin cambiar nada.
- **E2. Migración fallida** `[estado: ausente]` (paso 5): el programa no arranca sobre un esquema a medias; conserva la copia previa a la migración y lo informa (UC-01 A8, UC-23).
- **E3. Versión incompatible con la instalación** `[estado: ausente]` (paso 3): por ejemplo, otra plataforma o un esquema que no puede migrarse; el sistema lo informa y no propone instalarla.

## Postcondiciones

- La instalación está en la versión publicada o sin cambios; jobs, resultados, configuración y perfiles se conservan.

## Requisitos especiales

- El mecanismo depende del canal ([SUP-C12](../supplementary-specification.md)); no se elige todavía una estrategia universal.

## Reglas, requisitos y restricciones asociados

- [BR-51](../business-rules.md), BR-44; SUP-C10, SUP-C12; UC-01 A8, UC-23, UC-27.

## Criterios de aceptación

1. Una comprobación nunca instala nada por sí sola.
2. Una instalación de un canal nunca recibe una versión de otro canal.
3. Tras actualizar, los jobs pendientes y los resultados siguen disponibles.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Comprobación con un canal simulado (nueva, igual, inaccesible, incompatible) | Desarrollo |
| Migración de una base de datos de la versión anterior | Desarrollo |
