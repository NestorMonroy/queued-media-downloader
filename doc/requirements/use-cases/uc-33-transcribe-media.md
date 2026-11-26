# UC-33: Transcribir un medio

- **Objetivo:** el User obtiene el texto hablado de un audio o video, con marcas de tiempo por segmento, como un resultado propio que puede consultar, exportar y reutilizar.
- **Actor principal:** User
- **Disparador:** el User pide la transcripción de un resultado existente o de un archivo local.
- **Prioridad:** media.
- **Significativo para la arquitectura:** sí: primera operación que no es una descarga; resultado derivado con identidad propia (BR-55), modelo, recursos y cancelación distintos de los de yt-dlp.
- **Estado:** candidato (propuesta de la instrucción 2.6.0, pendiente de aprobación del Responsable). Horizonte: futuro. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (`asr_backend.py`, `subprocess_asr_base.py`: motores de transcripción aislados en un proceso hijo que convierte un fallo nativo en un job fallido; historial de transcripciones con límite de 200 entradas, copiar y exportar texto) y VoiceBlueprintPro (derivado de VoiceStudio). Evidencia y nivel en el [análisis de requisitos, §16](../requirements-analysis.md#16-descubrimiento-260-ia-privacidad-y-modelo-comercial).
- **Independencia:** UC-24 obtiene subtítulos publicados por el sitio sin procesar el audio; aquí el texto se produce a partir del audio. UC-36 da formato de subtítulos a una transcripción.

## Breve descripción

El User elige la entrada (un resultado registrado o un archivo local), el idioma hablado (o detección automática) y el modelo. El sistema crea un job de procesamiento, extrae el audio, ejecuta la transcripción por segmentos y registra la transcripción como resultado derivado de la entrada.

## Precondiciones

- UC-01 completado; al menos un modelo de transcripción disponible (UC-39).
- La entrada existe y es legible.

## Flujo básico

1. El User elige la entrada, el idioma hablado y el modelo.
2. El sistema calcula la identidad del resultado derivado ([BR-55](../business-rules.md)) y comprueba si ya existe uno equivalente.
3. El sistema crea un job de procesamiento con la admisión de recursos de la operación (diseño, §18.4).
4. El sistema extrae el audio de la entrada con ffmpeg a un resultado intermedio.
5. El sistema transcribe por segmentos y guarda cada segmento terminado como evidencia recuperable.
6. El sistema publica la transcripción (texto y segmentos con marcas de tiempo) como resultado del job y la registra con su procedencia: entrada, modelo y versión, parámetros.

## Flujos alternativos

- **A1. Transcripción equivalente existente** `[estado: ausente]` (paso 2): el sistema ofrece reutilizarla en lugar de procesar de nuevo.
- **A2. Detección automática del idioma** `[estado: ausente]` (paso 1): el modelo detecta el idioma; el detectado queda registrado con la transcripción.
- **A3. Reanudar tras una interrupción** `[estado: ausente]` (paso 5): los segmentos ya terminados no se repiten; se continúa desde el primero que falta.
- **A4. Cancelar** `[estado: ausente]` (paso 5): el job se cancela en el siguiente punto seguro; los segmentos terminados se descartan o se conservan según la política de recuperación, nunca como resultado publicado.
- **A5. Modelo no instalado** `[estado: ausente]` (paso 1): el sistema ofrece instalarlo con UC-39 antes de crear el job.

## Excepciones

- **E1. Recursos insuficientes** `[estado: ausente]` (paso 3): la admisión rechaza o aplaza el job con el recurso que falta (memoria, memoria de la GPU, disco); no se carga un modelo que no cabe.
- **E2. Fallo del motor** `[estado: ausente]` (paso 5): el motor falla o termina de forma anómala; el job falla con la condición clasificada y el proceso del producto sigue en pie.

## Postcondiciones

- Existe una transcripción registrada con la identidad de su entrada, modelo y parámetros, o el job terminó con una condición clasificada.
- La entrada no se modificó.

## Requisitos especiales

- Prueba sin modelos: un motor simulado con salida determinista (como `make test` en kimi-k3-in-c).

## Reglas, requisitos y restricciones asociados

- [BR-55](../business-rules.md) (propuesta), [BR-53](../business-rules.md); SUP-D03; UC-25, UC-26, UC-39; diseño, §18.

## Criterios de aceptación

1. Transcribir dos veces la misma entrada con el mismo modelo y parámetros ofrece reutilizar el resultado.
2. Una interrupción a mitad no repite los segmentos terminados.
3. Un fallo del motor no termina el proceso del producto.
4. La entrada queda intacta.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Transcripción con un motor simulado, interrupción y reanudación | Desarrollo |
| Rendimiento con un modelo real en el hardware objetivo | **Windows** |
