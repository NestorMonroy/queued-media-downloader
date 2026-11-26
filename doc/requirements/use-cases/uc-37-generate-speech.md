# UC-37: Generar voz

- **Objetivo:** el User obtiene audio hablado a partir de un texto, con una voz y un idioma elegidos.
- **Actor principal:** User
- **Disparador:** el User pide convertir un texto o una traducción en voz.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** sí: síntesis por fragmentos con recursos de GPU, modelos grandes y recuperación por fragmento.
- **Estado:** candidato (propuesta de la instrucción 2.6.0, pendiente de aprobación del Responsable). Horizonte: futuro. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (`chunked_tts.py`: texto largo dividido por frases y unido con fundido corto; `sentence_chunker.py`: segmentación de frases que admite abreviaturas y puntuación CJK; `docs/engine-acceptance.md`: cada motor ocupa un trabajo concreto). Evidencia y nivel en el [análisis de requisitos, §16](../requirements-analysis.md#16-descubrimiento-260-ia-privacidad-y-modelo-comercial).
- **Independencia:** UC-38 usa esta generación como etapa del doblaje; aquí el resultado es solo el audio.

## Breve descripción

El User elige el texto, la voz, el idioma y el modelo. El sistema divide el texto en frases, sintetiza cada fragmento y une el audio en un resultado registrado.

## Precondiciones

- Hay un modelo de voz disponible (UC-39).

## Flujo básico

1. El User elige el texto, la voz, el idioma y el modelo.
2. El sistema calcula la identidad del resultado y comprueba si ya existe uno equivalente.
3. El sistema crea un job de procesamiento y divide el texto en fragmentos por frase.
4. El sistema sintetiza cada fragmento y guarda cada uno terminado como evidencia recuperable.
5. El sistema une los fragmentos, escribe el audio con escritura atómica y lo registra como output.

## Flujos alternativos

- **A1. Reanudar** `[estado: ausente]` (paso 4): los fragmentos terminados no se repiten.
- **A2. Regenerar un fragmento** `[estado: ausente]` (paso 4): el User cambia el texto de un fragmento; solo se regenera ese fragmento, porque la identidad de los demás no cambió.

## Excepciones

- **E1. Recursos insuficientes** `[estado: ausente]` (paso 3): la admisión rechaza o aplaza el job con el recurso que falta.
- **E2. Fallo del motor** `[estado: ausente]` (paso 4): el job falla con la condición clasificada sin terminar el proceso del producto.

## Postcondiciones

- Existe un audio registrado con su procedencia, o el job terminó con una condición clasificada.

## Requisitos especiales

- La voz de una persona real no se clona sin las condiciones que decida el Responsable; este candidato no incluye clonación de voz.

## Reglas, requisitos y restricciones asociados

- [BR-55](../business-rules.md) (propuesta); UC-39; diseño, §18.

## Criterios de aceptación

1. Cambiar un fragmento regenera solo ese fragmento.
2. Una interrupción no repite fragmentos terminados.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Síntesis con un motor simulado, interrupción y regeneración parcial | Desarrollo |
