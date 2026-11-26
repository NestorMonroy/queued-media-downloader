# UC-38: Doblar un medio

- **Objetivo:** el User obtiene una versión de un video o audio con la voz en otro idioma, sincronizada con el original.
- **Actor principal:** User
- **Disparador:** el User pide doblar un resultado a un idioma.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** sí: composición de etapas (transcripción, traducción, voz, mezcla) con resultados intermedios, recuperación por etapa y varios outputs.
- **Estado:** candidato (propuesta de la instrucción 2.6.0, pendiente de aprobación del Responsable). Horizonte: futuro. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (`dub_pipeline.py`: copia atómica de la entrada al directorio del job, caché por hash del contenido, seguimiento y cancelación de los procesos de ffmpeg y separación de fondo; `dub_resume.py`: copia de recuperación de cada segmento terminado; `incremental.py`: solo se regeneran los segmentos cuyas entradas cambiaron; publicación de la pista al terminar). VoiceBlueprintPro hereda la misma canalización sin `dub_resume.py`. Evidencia y nivel en el [análisis de requisitos, §16](../requirements-analysis.md#16-descubrimiento-260-ia-privacidad-y-modelo-comercial).
- **Independencia:** Compone UC-33, UC-34 y UC-37 como etapas con identidad propia; no es un diseñador genérico de flujos de trabajo.

## Breve descripción

El sistema transcribe el medio, traduce la transcripción, genera la voz de cada segmento ajustada a su duración, la mezcla con el fondo y publica el medio doblado como output nuevo. Cada etapa produce un resultado intermedio con su identidad.

## Precondiciones

- UC-01 completado; modelos de transcripción, traducción y voz disponibles (UC-39) o proveedores configurados.

## Flujo básico

1. El User elige el medio, el idioma de destino y las voces.
2. El sistema calcula las identidades de las etapas y reutiliza las que ya existen.
3. El sistema transcribe (UC-33) y traduce (UC-34) como etapas.
4. El sistema genera la voz de cada segmento (UC-37) ajustada a su duración.
5. El sistema separa el fondo si se pidió, mezcla la voz con el fondo y compone el medio doblado con ffmpeg.
6. El sistema publica el medio doblado como output nuevo, con reclamación, y conserva el original.

## Flujos alternativos

- **A1. Revisar antes de generar** `[estado: ausente]` (paso 3): el User revisa y corrige la traducción; la corrección invalida solo las etapas posteriores de los segmentos afectados.
- **A2. Subtítulos como entrada** `[estado: ausente]` (paso 3): el User aporta subtítulos en lugar de transcribir; se validan y se usan como transcripción con esa procedencia.
- **A3. Reanudar tras un cierre** `[estado: ausente]` (paso 4): las etapas y los segmentos terminados no se repiten.
- **A4. Cancelar** `[estado: ausente]` (paso 4): se cancela en el siguiente punto seguro; los resultados intermedios terminados quedan como evidencia según la política de recuperación y nada se publica a medias.

## Excepciones

- **E1. Una etapa falla** `[estado: ausente]` (paso 3): el job falla en esa etapa con la condición clasificada; las etapas anteriores terminadas se conservan para reanudar.
- **E2. Recursos insuficientes** `[estado: ausente]` (paso 4): la admisión aplaza la etapa con el recurso que falta.

## Postcondiciones

- Existe un medio doblado registrado como output nuevo, o el job terminó con una condición clasificada en una etapa identificada.
- El medio original no cambió.

## Requisitos especiales

- Varios outputs por job (D-15): pista de voz, medio doblado y, si se piden, subtítulos.

## Reglas, requisitos y restricciones asociados

- [BR-53](../business-rules.md), [BR-55](../business-rules.md) (propuesta); D-15; UC-33, UC-34, UC-36, UC-37, UC-39; diseño, §18.3.

## Criterios de aceptación

1. Un cierre a mitad no repite las etapas terminadas.
2. Corregir un segmento regenera solo ese segmento en las etapas posteriores.
3. El original queda intacto y el doblado es un output nuevo reclamado.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Canalización completa con motores simulados, cierre a mitad y corrección parcial | Desarrollo |
