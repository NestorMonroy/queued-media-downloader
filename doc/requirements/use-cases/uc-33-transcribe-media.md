# UC-33: Transcribir un medio

- **Objetivo:** el User obtiene el texto hablado de un audio o un video, con segmentos y marcas de tiempo, como un resultado que puede consultar, corregir, exportar y reutilizar.
- **Actor principal:** User
- **Disparador:** el User pide la transcripción de un medio local, de un resultado ya obtenido o de un contenido remoto compatible.
- **Prioridad:** media.
- **Significativo para la arquitectura:** sí: primer resultado derivado (BR-55, ADR-0035), con recursos, cancelación y recuperación distintos de los de yt-dlp.
- **Estado:** aceptado (Responsable, instrucción 2.7.0): el objetivo y su flujo básico están en el alcance del producto. Los flujos alternativos y de excepción son propuestas (instrucciones 2.6.0 y 2.7.0) pendientes de aprobación: aceptar el objetivo no aprueba todos sus flujos, mecanismos, modelos ni runtimes. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (`asr_backend.py`, `subprocess_asr_base.py`; historial de transcripciones; exportación de texto) como evidencia de flujos; orientación estratégica aprobada en la instrucción 2.6.0 y objetivo aceptado en la 2.7.0. Evidencia en el [análisis, §16.2 y §17](../requirements-analysis.md#17-consolidación-270).
- **Independencia:** UC-24 **obtiene** subtítulos o transcripciones que ya publica el sitio; aquí se **generan** a partir del audio. UC-36 convierte una transcripción en subtítulos sincronizados. UC-34 traduce.

## Breve descripción

El User elige la entrada: un archivo de audio o video local, un resultado ya obtenido (UC-25) o un contenido remoto compatible, del que basta obtener el audio. Indica el idioma hablado o pide detectarlo, y elige un modelo instalado (UC-39). El sistema produce una transcripción con segmentos y marcas de tiempo y la registra como resultado derivado de su entrada, con su especificación de procesamiento.

## Precondiciones

- UC-01 completado; existe al menos un modelo de transcripción utilizable en el equipo (UC-39) o un proveedor configurado por el User.
- La entrada existe y es legible, o es un contenido remoto compatible.

## Flujo básico

1. El User elige la entrada, el idioma hablado (o la detección) y el modelo.
2. El sistema calcula la especificación de procesamiento y busca un resultado reutilizable que cumpla las condiciones de [BR-55](../business-rules.md).
3. Si no lo hay, el sistema crea un job de transcripción admitido según los recursos de la operación (diseño, §18.4).
4. El sistema prepara la entrada de audio: la extrae del archivo local o del resultado, o la obtiene del contenido remoto sin exigir el video completo.
5. El sistema transcribe por segmentos y conserva cada segmento terminado como evidencia de recuperación.
6. El sistema publica la transcripción (texto, segmentos, marcas de tiempo e idioma) como resultado del job, con su procedencia.

## Flujos alternativos

- **A1. Reutilizar una transcripción existente** `[estado: ausente; propuesto]` (paso 2): hay un resultado que cumple BR-55; el sistema lo ofrece y el User decide reutilizarlo o generar otro.
- **A2. Obtener una transcripción ya publicada** `[estado: ausente; propuesto]` (paso 1): el contenido remoto publica subtítulos o transcripción; el sistema ofrece obtenerla con UC-24 en lugar de generarla.
- **A3. Detección de idioma** `[estado: ausente; propuesto]` (paso 1): el modelo detecta el idioma; el detectado queda registrado con la transcripción.
- **A4. Identificación de hablantes** `[estado: ausente; propuesto]` (paso 5): el User pide distinguir hablantes; si el modelo o un componente de diarización lo admite, cada segmento lleva una etiqueta de hablante; si no, el sistema lo indica antes de empezar.
- **A5. Reanudar tras una interrupción** `[estado: ausente; propuesto]` (paso 5): los segmentos con evidencia válida no se repiten; se continúa desde el primero que falta, sin publicar nada a medias.
- **A6. Corregir la transcripción** `[estado: ausente; propuesto]` (paso 6): el User edita el texto o las marcas de tiempo de uno o varios segmentos; la corrección crea una nueva revisión del resultado y conserva la anterior.
- **A7. Reprocesar una selección** `[estado: ausente; propuesto]` (paso 6): el User pide transcribir de nuevo solo algunos segmentos, con otro modelo o parámetros; los demás se conservan y la nueva revisión registra qué segmentos cambiaron.
- **A8. Exportar** `[estado: ausente; propuesto]` (paso 6): el User exporta la transcripción como texto o en un formato con marcas de tiempo; la exportación es una copia (BR-52).
- **A9. Cancelar** `[estado: ausente; propuesto]` (paso 5): el job se cancela en el siguiente punto seguro; los segmentos terminados se conservan o descartan según su contrato de recuperación y nunca se publican como resultado completo.

## Excepciones

- **E1. Recursos no disponibles** `[estado: ausente; propuesto]` (paso 3): falta o está ocupado un recurso que la operación necesita (memoria, memoria de GPU, disco); la admisión aplaza o rechaza el job con el recurso concreto.
- **E2. Fallo del motor** `[estado: ausente; propuesto]` (paso 5): el motor falla o termina de forma anómala; el job falla con una condición clasificada y el proceso del producto sigue funcionando.
- **E3. Entrada sin audio utilizable** `[estado: ausente; propuesto]` (paso 4): la entrada no tiene pista de audio o no se puede decodificar; el job falla con esa condición.

## Postcondiciones

- Existe una transcripción registrada con su procedencia, o el job terminó con una condición clasificada.
- La entrada no cambió.

## Requisitos especiales

- Las pruebas automáticas no necesitan modelos: un motor simulado determinista sustituye al real.
- La igualdad de petición no implica igualdad binaria del resultado (diseño, §18.2).

## Reglas, requisitos y restricciones asociados

- [BR-52](../business-rules.md), [BR-55](../business-rules.md); UC-24, UC-25, UC-26, UC-39; diseño, §18.

## Criterios de aceptación

1. Una transcripción se registra con su entrada, modelo, versión y parámetros que la afectan.
2. Una interrupción no repite segmentos con evidencia válida ni publica un resultado incompleto.
3. Un contenido remoto se transcribe sin exigir el video completo cuando basta el audio.
4. Una corrección conserva la revisión anterior.
5. Un fallo del motor no termina el proceso del producto.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Motor simulado: interrupción, reanudación, corrección y reproceso de una selección | Desarrollo |
| Rendimiento y calidad con un modelo real en el hardware objetivo | **Windows** |
