# UC-35: Resumir el contenido de un medio

- **Objetivo:** el User obtiene un resumen breve del contenido hablado de un medio, a partir de su transcripción.
- **Actor principal:** User
- **Disparador:** el User pide un resumen de un resultado o de una transcripción.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** sí: requiere un modelo de lenguaje, local o remoto, con recursos distintos de los de la transcripción.
- **Estado:** candidato (propuesta de la instrucción 2.6.0, pendiente de aprobación del Responsable). Horizonte: futuro. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** Sin evidencia de implementación en las referencias revisadas: VoiceStudio no tiene resumen de contenido (sus funciones `summary` son de estadísticas y discos). VidBee anuncia transcripción e IA (N70, §15). Objetivo de la orientación estratégica de la instrucción 2.6.0. Evidencia y nivel en el [análisis de requisitos, §16](../requirements-analysis.md#16-descubrimiento-260-ia-privacidad-y-modelo-comercial).
- **Independencia:** UC-33 produce el texto; aquí se condensa. UC-24 obtiene la descripción publicada por el sitio, que no es un resumen del contenido.

## Breve descripción

El sistema usa la transcripción registrada (o la crea con UC-33) y produce un resumen con el modelo elegido, registrado como resultado derivado.

## Precondiciones

- Existe una transcripción registrada o se puede crear (UC-33).
- Hay un modelo de lenguaje disponible: local (UC-39) o un proveedor configurado por el User.

## Flujo básico

1. El User elige la entrada, la longitud del resumen y el modelo.
2. El sistema obtiene la transcripción registrada de la entrada.
3. El sistema calcula la identidad del resultado derivado y comprueba si ya existe uno equivalente.
4. El sistema crea un job de procesamiento y genera el resumen.
5. El sistema publica el resumen como resultado del job con su procedencia.

## Flujos alternativos

- **A1. Sin transcripción previa** `[estado: ausente]` (paso 2): el sistema crea primero la transcripción (UC-33) como etapa del mismo procesamiento, con su propia identidad.
- **A2. Transcripción larga** `[estado: ausente]` (paso 4): el texto excede el contexto del modelo; el sistema resume por partes y combina, y lo registra en la procedencia.

## Excepciones

- **E1. Modelo no disponible o recursos insuficientes** `[estado: ausente]` (paso 4): el job falla o se aplaza con la condición clasificada.

## Postcondiciones

- Existe un resumen registrado con su procedencia, o el job terminó con una condición clasificada.

## Requisitos especiales

- El resumen se presenta como generado por un modelo, sin afirmar exactitud.

## Reglas, requisitos y restricciones asociados

- [BR-55](../business-rules.md) (propuesta); UC-33, UC-39.

## Criterios de aceptación

1. El resumen registra la transcripción, el modelo y los parámetros de los que procede.
2. Sin transcripción previa, la transcripción creada queda también registrada y reutilizable.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Resumen con un modelo simulado y una transcripción larga | Desarrollo |
