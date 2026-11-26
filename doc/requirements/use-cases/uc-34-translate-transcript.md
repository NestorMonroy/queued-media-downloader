# UC-34: Traducir una transcripción

- **Objetivo:** el User obtiene una transcripción en otro idioma conservando la segmentación y las marcas de tiempo del original.
- **Actor principal:** User
- **Disparador:** el User pide traducir una transcripción a uno o varios idiomas.
- **Prioridad:** media.
- **Significativo para la arquitectura:** sí: resultado derivado de otro resultado derivado; motores locales o remotos con secretos del User.
- **Estado:** candidato (propuesta de la instrucción 2.6.0, pendiente de aprobación del Responsable). Horizonte: futuro. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (`docs/dubbing/translation-engines.md`: Argos y NLLB-200 sin conexión; Google, DeepL, Microsoft, MyMemory y un servicio compatible con OpenAI en línea, algunos con clave; traducción pegada por el User). Evidencia y nivel en el [análisis de requisitos, §16](../requirements-analysis.md#16-descubrimiento-260-ia-privacidad-y-modelo-comercial).
- **Independencia:** UC-33 produce la transcripción; aquí se cambia su idioma. UC-18 A9 fija preferencias de idioma de descarga, no traduce.

## Breve descripción

El User elige una transcripción registrada, el idioma de destino y el motor de traducción. El sistema traduce por segmentos y registra la traducción como resultado derivado de la transcripción.

## Precondiciones

- Existe una transcripción registrada (UC-33) o importada.
- Hay un motor de traducción disponible: local (UC-39) o un proveedor configurado por el User.

## Flujo básico

1. El User elige la transcripción, el idioma de destino y el motor.
2. El sistema calcula la identidad del resultado derivado y comprueba si ya existe uno equivalente.
3. El sistema crea un job de procesamiento.
4. El sistema traduce segmento a segmento, conservando las marcas de tiempo.
5. El sistema publica la traducción como resultado del job con su procedencia.

## Flujos alternativos

- **A1. Varios idiomas** `[estado: ausente]` (paso 1): se crea un job por idioma, independientes entre sí.
- **A2. Proveedor remoto configurado por el User** `[estado: ausente]` (paso 1): el sistema avisa de que el texto sale del equipo hacia el proveedor elegido; la clave se guarda como credencial (SUP-SEC01).
- **A3. Traducción aportada por el User** `[estado: ausente]` (paso 4): el User pega o importa una traducción; el sistema la alinea con los segmentos y la registra con esa procedencia.
- **A4. Revisar y corregir** `[estado: ausente]` (paso 5): el User edita segmentos traducidos; la edición crea una nueva revisión del resultado y no altera la anterior.

## Excepciones

- **E1. Proveedor inaccesible o sin crédito** `[estado: ausente]` (paso 4): el job falla con la condición clasificada; los segmentos traducidos se conservan para reanudar.
- **E2. Par de idiomas no admitido** `[estado: ausente]` (paso 1): el motor no admite el par; no se crea el job.

## Postcondiciones

- Existe una traducción registrada con su procedencia, o el job terminó con una condición clasificada.
- La transcripción de origen no cambió.

## Requisitos especiales

- Ningún texto sale del equipo sin un proveedor remoto elegido por el User.

## Reglas, requisitos y restricciones asociados

- [BR-55](../business-rules.md) (propuesta); SUP-SEC01, SUP-SEC07; UC-33, UC-39.

## Criterios de aceptación

1. La traducción conserva el número de segmentos y sus marcas de tiempo.
2. Con un motor local no hay tráfico de red.
3. Editar un segmento no modifica la revisión anterior.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Traducción con un motor simulado y un proveedor remoto simulado que falla | Desarrollo |
