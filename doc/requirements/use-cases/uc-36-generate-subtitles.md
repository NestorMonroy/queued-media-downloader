# UC-36: Generar subtítulos

- **Objetivo:** el User obtiene un archivo de subtítulos (SRT o WebVTT) a partir de una transcripción o una traducción, para usarlo con el medio.
- **Actor principal:** User
- **Disparador:** el User pide subtítulos de un resultado.
- **Prioridad:** media.
- **Significativo para la arquitectura:** no por sí solo: da formato a un resultado derivado; reutiliza la identidad y el registro de outputs.
- **Estado:** candidato (propuesta de la instrucción 2.6.0, pendiente de aprobación del Responsable). Horizonte: futuro. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (`docs/dub-subtitle-input.md`: validación de SRT sin crear job; `subtitle_segmenter.py`, `fitted_subtitles.py`: segmentación de subtítulos). Evidencia y nivel en el [análisis de requisitos, §16](../requirements-analysis.md#16-descubrimiento-260-ia-privacidad-y-modelo-comercial).
- **Independencia:** UC-24 descarga subtítulos publicados; aquí se generan desde el audio. UC-03 A16 incrusta subtítulos descargados.

## Breve descripción

El User elige una transcripción o traducción registrada y un formato. El sistema segmenta las líneas según límites de lectura y escribe el archivo como output del job, junto al medio o en el destino elegido.

## Precondiciones

- Existe una transcripción (UC-33) o traducción (UC-34) registrada.

## Flujo básico

1. El User elige la transcripción o traducción, el formato y el destino.
2. El sistema calcula la identidad del resultado y comprueba si ya existe uno equivalente.
3. El sistema segmenta las líneas con límites de longitud y duración.
4. El sistema escribe el archivo con escritura atómica y lo registra como output con reclamación (ADR-0033).
5. El sistema informa de la ruta del archivo.

## Flujos alternativos

- **A1. Incrustar en el medio** `[estado: ausente]` (paso 4): el User pide un medio con los subtítulos incrustados; se crea un output nuevo y el original no cambia.
- **A2. Archivo existente con el mismo nombre** `[estado: ausente]` (paso 4): se aplica la política de colisión; solo se reemplaza por petición explícita ([BR-53](../business-rules.md)).

## Excepciones

- **E1. Destino sin espacio o sin escritura** `[estado: ausente]` (paso 4): el job falla con la condición de almacenamiento clasificada (UC-17).

## Postcondiciones

- Existe un archivo de subtítulos registrado y reclamado, o el job terminó con una condición clasificada.

## Requisitos especiales

- Los subtítulos generados se pueden validar con el mismo validador que los importados.

## Reglas, requisitos y restricciones asociados

- [BR-53](../business-rules.md), [BR-55](../business-rules.md) (propuesta); UC-17, UC-25; ADR-0033.

## Criterios de aceptación

1. El archivo generado es SRT o WebVTT válido.
2. Incrustar no modifica el medio original.
3. Un archivo existente no se reemplaza sin petición explícita.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Generación desde una transcripción fija y validación del formato | Cualquier sistema |
