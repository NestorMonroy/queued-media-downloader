# UC-36: Generar subtítulos

- **Objetivo:** el User obtiene subtítulos sincronizados a partir de una transcripción o una traducción, los ajusta y los exporta o los incorpora a un medio.
- **Actor principal:** User
- **Disparador:** el User pide subtítulos de un medio.
- **Prioridad:** media.
- **Significativo para la arquitectura:** no por sí solo: da formato y sincronización a un resultado derivado; reutiliza la identidad y el registro de outputs.
- **Estado:** aceptado (Responsable, instrucción 2.7.0): el objetivo y su flujo básico están en el alcance del producto. Los flujos alternativos y de excepción son propuestas (instrucciones 2.6.0 y 2.7.0) pendientes de aprobación: aceptar el objetivo no aprueba todos sus flujos, mecanismos, modelos ni runtimes. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (`subtitle_segmenter.py`, `fitted_subtitles.py`, validación de SRT sin crear job). Objetivo aceptado en la instrucción 2.7.0.
- **Independencia:** UC-24 **obtiene** subtítulos existentes; UC-33 genera el texto; UC-34 traduce (también subtítulos); aquí se generan subtítulos sincronizados, se ajustan y se exportan.

## Breve descripción

Una transcripción es texto con marcas de tiempo; unos subtítulos son líneas sincronizadas con límites de lectura. El sistema segmenta el texto en líneas, permite ajustar el texto, la segmentación y la sincronización, y escribe el formato elegido.

## Precondiciones

- Existe una transcripción (UC-33), una traducción (UC-34) o unos subtítulos existentes.

## Flujo básico

1. El User elige la entrada, el formato y el destino.
2. El sistema busca un resultado reutilizable según BR-55.
3. El sistema segmenta el texto en líneas con límites de longitud y duración.
4. El sistema escribe el archivo con escritura atómica y lo registra como output reclamado (ADR-0033).
5. El sistema informa de la ruta del archivo.

## Flujos alternativos

- **A1. Partir de subtítulos existentes** `[estado: ausente; propuesto]` (paso 1): la entrada son subtítulos obtenidos (UC-24) o importados; el sistema los valida y permite ajustarlos sin generarlos.
- **A2. Ajustar texto** `[estado: ausente; propuesto]` (paso 3): el User corrige el texto de una o varias líneas.
- **A3. Ajustar segmentación** `[estado: ausente; propuesto]` (paso 3): el User une o divide líneas o cambia los límites.
- **A4. Ajustar sincronización** `[estado: ausente; propuesto]` (paso 3): el User desplaza o estira los tiempos de una línea, de una selección o de todo el archivo.
- **A5. Otro formato** `[estado: ausente; propuesto]` (paso 4): el User elige otro de los formatos admitidos; no hay un formato único impuesto.
- **A6. Incorporar a un medio** `[estado: ausente; propuesto]` (paso 4): el User pide un medio con los subtítulos incorporados; se crea un output nuevo y el medio original no cambia.
- **A7. Archivo existente con el mismo nombre** `[estado: ausente; propuesto]` (paso 4): se aplica la política de colisión; solo se reemplaza por petición explícita ([BR-53](../business-rules.md)).

## Excepciones

- **E1. Destino sin espacio o sin escritura** `[estado: ausente; propuesto]` (paso 4): el job falla con la condición de almacenamiento clasificada (UC-17).
- **E2. Subtítulos inválidos** `[estado: ausente; propuesto]` (paso 1): la entrada no se puede validar; no se crea el job.

## Postcondiciones

- Existe un archivo de subtítulos registrado y reclamado, o el job terminó con una condición clasificada.
- Ninguna entrada cambió.

## Requisitos especiales

- Los formatos se eligen por necesidades demostradas; SRT y WebVTT tienen evidencia en las referencias.

## Reglas, requisitos y restricciones asociados

- [BR-52](../business-rules.md), [BR-53](../business-rules.md), [BR-55](../business-rules.md); UC-17, UC-24, UC-25; ADR-0033.

## Criterios de aceptación

1. Los subtítulos escritos son válidos en el formato elegido.
2. Ajustar la sincronización no cambia el texto, y viceversa.
3. Incorporar los subtítulos no modifica el medio original.
4. Un archivo existente no se reemplaza sin petición explícita.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Generación, ajuste y validación de formatos desde una transcripción fija | Cualquier sistema |
