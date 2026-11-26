# UC-27: Administrar las dependencias multimedia

- **Objetivo:** el User sabe qué versiones de yt-dlp, yt-dlp-ejs, deno y ffmpeg usa y si son las cualificadas. Cuando un sitio cambia, puede pasar a una versión candidata sin esperar una versión del programa y volver a la cualificada si algo falla, sin perder la reproducibilidad.
- **Actor principal:** User
- **Actor secundario:** Mantenedor (cualifica las versiones con las pruebas de contrato)
- **Disparador:** un extractor deja de funcionar (`EXTRACTOR_OUTDATED`), o `diagnose` avisa de una versión que no es la cualificada.
- **Relación:** UC-01 ya muestra versiones y verifica ffmpeg y deno; este caso de uso añade el cambio controlado. Sustituye al candidato «Actualizar yt-dlp».
- **Prioridad:** media
- **Significativo para la arquitectura:** sí; contradice en parte ADR-0002 si D-8 admite versiones no cualificadas
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: ausente (`diagnose` informa de las versiones). Condición técnica: D-8; la versión candidata no cualificada (A2) queda condicionada.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:**
  - **VoiceStudio:** capa de yt-dlp actualizada desde PyPI y «Restore tested version».
  - **Seal:** canales de actualización.
  - **Kannagi:** comprobación diaria.
  - **Producto:** ADR-0002, SUP-S01 y el procedimiento de actualización.

## Breve descripción

Las capacidades se reparten entre tres responsables:
- **User:**
  - consultar las versiones (UC-01);
  - consultar si hay una versión cualificada más nueva publicada por el Mantenedor;
  - pasar a ella;
  - volver a la anterior.
- **User, con aviso explícito** (solo si D-8 lo permite): probar una versión no cualificada de yt-dlp.
- **Mantenedor:** cualificar versiones con las pruebas de contrato (SUP-S01).

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User ejecuta `dependencies show`.
2. El sistema muestra cada dependencia con su versión en uso, la cualificada y su origen (incluida, del sistema o configurada).
3. Si una versión no coincide con la cualificada, lo marca y explica el riesgo.

## Flujos alternativos

- **A1. Pasar a una versión cualificada publicada:** `[estado: ausente]` equivale a actualizar el programa (`git pull`, `uv sync`); el sistema indica la orden exacta.
- **A2. Versión candidata no cualificada** `[estado: ausente; condicionado]` (D-8): `dependencies try yt-dlp==X` instala la versión en un entorno separado del cualificado, la usa solo con `--candidate` y la marca en el log, en `diagnose` y en el informe (UC-16).
- **A3. Volver a la cualificada:** `[estado: ausente]` `dependencies restore` descarta la candidata.
- **A4. ffmpeg propio:** `[estado: ausente]` `ffmpeg_path` (UC-01 A4), con el aviso de versión no validada.
- **A5. Dependencia incompatible:** `[estado: ausente]` una combinación conocida como incompatible (por ejemplo, un yt-dlp-ejs que no corresponde a yt-dlp) se informa como fallo de `diagnose`.

## Excepciones

- **E1. Sin conexión al consultar versiones publicadas:** `[estado: ausente]` se informa; lo local se muestra igual.
- **E2. Instalación de una candidata fallida:** `[estado: ausente]` la cualificada sigue intacta.

## Garantías

- **De éxito:** el User sabe qué usa y puede volver a lo cualificado.
- **Mínima:** nunca hay actualizaciones automáticas, y la versión cualificada nunca se reemplaza sin una acción del User.

## Reglas, requisitos y restricciones asociados

- **Requisitos suplementarios:** SUP-S01, SUP-C02 y SUP-O02.
- **Restricciones:** ADR-0002; las pruebas de contrato son la cualificación.
- **Dependencias:** UC-01 y UC-16; D-8.

## Criterios de aceptación

1. `dependencies show` coincide con lo que carga `run`.
2. Una versión candidata nunca se usa sin `--candidate` y siempre queda marcada.
3. `restore` deja el entorno cualificado, comprobado con `diagnose`.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Versiones en uso frente a cualificadas, combinación incompatible | Cualquier sistema |
| Candidata y vuelta atrás | Cualquier sistema (solo si D-8 lo aprueba) |
