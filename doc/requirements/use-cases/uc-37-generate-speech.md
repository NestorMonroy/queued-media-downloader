# UC-37: Generar voz

- **Objetivo:** el User obtiene audio hablado a partir de un texto, con un idioma, una voz y unas indicaciones de pronunciación, velocidad y pausas.
- **Actor principal:** User
- **Disparador:** el User pide convertir un texto, una traducción o unos subtítulos en voz.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** sí: síntesis por fragmentos con recursos de GPU, recuperación por fragmento y cancelación de inferencia (diseño, §18.4).
- **Estado:** aceptado (Responsable, instrucción 2.7.0): el objetivo y su flujo básico están en el alcance del producto. Los flujos alternativos y de excepción son propuestas (instrucciones 2.6.0 y 2.7.0) pendientes de aprobación: aceptar el objetivo no aprueba todos sus flujos, mecanismos, modelos ni runtimes. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (`chunked_tts.py`, `sentence_chunker.py`, tabla `voice_profiles`). Objetivo aceptado en la instrucción 2.7.0.
- **Independencia:** UC-38 usa la voz como etapa posible de un doblaje; UC-43 (candidato) administra voces reutilizables; aquí el resultado es solo audio.

## Breve descripción

El User elige el texto (o un texto temporizado), el idioma, la voz y las indicaciones. El sistema divide el texto en fragmentos, sintetiza cada uno y compone el audio. Con texto temporizado, puede ajustar cada fragmento a su duración.

## Precondiciones

- Hay un modelo de voz utilizable (UC-39) o un proveedor configurado por el User.

## Flujo básico

1. El User elige el texto, el idioma, la voz y el formato de salida.
2. El sistema busca un resultado reutilizable según BR-55.
3. El sistema crea un job y divide el texto en fragmentos.
4. El sistema sintetiza cada fragmento y conserva cada uno terminado como evidencia de recuperación.
5. El sistema compone el audio, lo escribe con escritura atómica y lo registra como output.

## Flujos alternativos

- **A1. Pronunciación, velocidad y pausas** `[estado: ausente; propuesto]` (paso 1): el User indica pronunciaciones, velocidad o pausas; el motor las aplica si las admite y el sistema informa de las que no.
- **A2. Ajustar a una duración** `[estado: ausente; propuesto]` (paso 4): con texto temporizado, cada fragmento se ajusta a la duración de su segmento dentro de los límites que admita el motor.
- **A3. Reanudar** `[estado: ausente; propuesto]` (paso 4): los fragmentos con evidencia válida no se repiten.
- **A4. Regenerar una sección** `[estado: ausente; propuesto]` (paso 5): el User cambia el texto, la voz o las indicaciones de uno o varios fragmentos; solo se regeneran esos y se recompone el audio.
- **A5. Cancelar** `[estado: ausente; propuesto]` (paso 4): la cancelación se pide y el sistema la confirma solo cuando el motor ha terminado y liberado sus recursos (diseño, §18.4).

## Excepciones

- **E1. Recursos no disponibles** `[estado: ausente; propuesto]` (paso 3): la admisión aplaza o rechaza el job con el recurso concreto.
- **E2. Fallo del motor** `[estado: ausente; propuesto]` (paso 4): el job falla con la condición clasificada sin terminar el proceso del producto.

## Postcondiciones

- Existe un audio registrado con su procedencia, o el job terminó con una condición clasificada.

## Requisitos especiales

- La generación no presupone clonación de voz. La clonación de voz está fuera del dominio según la Visión (disposición vigente desde `7dc9842`); su revisión es una cuestión abierta del Responsable, no de esta especificación.

## Reglas, requisitos y restricciones asociados

- [BR-55](../business-rules.md); UC-38, UC-39, UC-43 (candidato); diseño, §18.

## Criterios de aceptación

1. Cambiar un fragmento regenera solo ese fragmento y recompone el audio.
2. Una interrupción no repite fragmentos con evidencia válida.
3. Un recurso no se declara liberado mientras el motor lo usa.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Motor simulado: fragmentos, interrupción, regeneración parcial y cancelación | Desarrollo |
