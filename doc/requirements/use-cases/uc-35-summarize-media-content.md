# UC-35: Resumir el contenido de un medio

- **Objetivo:** el User obtiene un resumen del contenido hablado de un medio, general o por secciones, en el idioma y con el nivel de detalle que pide.
- **Actor principal:** User
- **Disparador:** el User pide un resumen de un medio, de una transcripción o de una traducción.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** sí: modelo de lenguaje local o remoto con recursos distintos de los de la transcripción.
- **Estado:** aceptado (Responsable, instrucción 2.7.0): el objetivo y su flujo básico están en el alcance del producto. Los flujos alternativos y de excepción son propuestas (instrucciones 2.6.0 y 2.7.0) pendientes de aprobación: aceptar el objetivo no aprueba todos sus flujos, mecanismos, modelos ni runtimes. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** Necesidad aceptada en la instrucción 2.7.0 con independencia de las referencias: en las revisadas no se identificó un flujo completo de resumen de contenido (las funciones llamadas `summary` de VoiceStudio son estadísticas, no un flujo de resumen).
- **Independencia:** UC-33 produce el texto; aquí se condensa. La descripción que publica el sitio (UC-24) no es un resumen del contenido.

## Breve descripción

El sistema parte de una transcripción registrada —o la crea con UC-33— y produce un resumen con el modelo elegido. El resumen puede ser general, por secciones o capítulos, o de ideas principales, y puede citar los segmentos de los que procede.

## Precondiciones

- Existe una transcripción registrada o se puede crear (UC-33).
- Hay un modelo de lenguaje disponible: local (UC-39) o un proveedor configurado por el User.

## Flujo básico

1. El User elige la entrada, el tipo de resumen, el idioma, el nivel de detalle y el modelo.
2. El sistema obtiene la transcripción de la entrada.
3. El sistema busca un resultado reutilizable según BR-55.
4. Si no lo hay, el sistema crea un job y genera el resumen.
5. El sistema publica el resumen como resultado del job, con su procedencia y las referencias a segmentos cuando existen.

## Flujos alternativos

- **A1. Sin transcripción previa** `[estado: ausente; propuesto]` (paso 2): el sistema crea primero la transcripción (UC-33), que queda registrada y reutilizable.
- **A2. Por secciones o capítulos** `[estado: ausente; propuesto]` (paso 1): el sistema usa los capítulos del medio, si existen, o una segmentación del texto, y resume cada parte.
- **A3. Ideas principales** `[estado: ausente; propuesto]` (paso 1): el resultado es una lista de ideas con referencia a sus segmentos.
- **A4. Texto largo** `[estado: ausente; propuesto]` (paso 4): el texto excede el contexto del modelo; el sistema resume por partes y combina, y lo registra en la procedencia.
- **A5. Exportar** `[estado: ausente; propuesto]` (paso 5): el User exporta el resumen como copia (BR-52).

## Excepciones

- **E1. Modelo no disponible o recursos insuficientes** `[estado: ausente; propuesto]` (paso 4): el job falla o se aplaza con la condición clasificada.

## Postcondiciones

- Existe un resumen registrado con su procedencia, o el job terminó con una condición clasificada.

## Requisitos especiales

- El resumen se presenta como generado por un modelo.
- Criterios de evaluación por cualificar, sin umbrales: fidelidad al contenido, cobertura de las secciones y errores (afirmaciones ausentes del texto).

## Reglas, requisitos y restricciones asociados

- [BR-52](../business-rules.md), [BR-55](../business-rules.md); UC-33, UC-39.

## Criterios de aceptación

1. El resumen registra la transcripción, el modelo y los parámetros de los que procede.
2. Un resumen por secciones cubre cada sección o indica cuáles omite.
3. Las referencias a segmentos apuntan a segmentos existentes de la transcripción.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Modelo simulado: resumen general, por secciones y de un texto largo | Desarrollo |
