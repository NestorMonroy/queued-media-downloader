# UC-34: Traducir una transcripción

- **Objetivo:** el User obtiene un texto en otro idioma a partir de una transcripción, unos subtítulos o un texto, conservando la segmentación y las marcas de tiempo cuando existen.
- **Actor principal:** User
- **Disparador:** el User pide traducir un texto temporizado o no temporizado a uno o varios idiomas.
- **Prioridad:** media.
- **Significativo para la arquitectura:** sí: resultado derivado de otro resultado o de una entrada del User; motores locales o remotos con secretos del User.
- **Estado:** aceptado (Responsable, instrucción 2.7.0): el objetivo y su flujo básico están en el alcance del producto. Los flujos alternativos y de excepción son propuestas (instrucciones 2.6.0 y 2.7.0) pendientes de aprobación: aceptar el objetivo no aprueba todos sus flujos, mecanismos, modelos ni runtimes. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (`docs/dubbing/translation-engines.md`: motores sin conexión, servicios en línea y traducción aportada por el User). Objetivo aceptado en la instrucción 2.7.0.
- **Independencia:** UC-33 genera la transcripción; UC-36 da formato de subtítulos; UC-37 genera voz. La traducción de subtítulos se hace aquí (A2) y UC-36 se limita a la sincronización y al formato.

## Breve descripción

La entrada puede ser una transcripción (UC-33, corregida o no), unos subtítulos existentes, un texto importado o una selección de segmentos. El sistema traduce con el motor elegido —sin imponer un modelo de lenguaje como único mecanismo— y registra el resultado como derivado de su entrada.

## Precondiciones

- Existe la entrada textual.
- Hay un motor de traducción disponible: local (UC-39) o un proveedor configurado por el User.

## Flujo básico

1. El User elige la entrada, el idioma de destino y el motor.
2. El sistema busca un resultado reutilizable según BR-55.
3. Si no lo hay, el sistema crea un job de traducción.
4. El sistema traduce por segmentos, conservando sus marcas de tiempo cuando existen.
5. El sistema publica la traducción como resultado del job, con su procedencia.

## Flujos alternativos

- **A1. Varios idiomas** `[estado: ausente; propuesto]` (paso 1): se crea un job por idioma, independientes entre sí.
- **A2. Traducir subtítulos** `[estado: ausente; propuesto]` (paso 1): la entrada es un archivo de subtítulos; se valida, se traduce conservando sus tiempos y el resultado puede exportarse como subtítulos (UC-36) sin repetir ninguna transcripción.
- **A3. Texto sin marcas de tiempo** `[estado: ausente; propuesto]` (paso 1): la entrada es texto importado; el resultado es texto traducido sin segmentos temporales.
- **A4. Selección de segmentos** `[estado: ausente; propuesto]` (paso 1): el User traduce o vuelve a traducir solo algunos segmentos; el resto de la revisión se conserva.
- **A5. Proveedor remoto** `[estado: ausente; propuesto]` (paso 1): el sistema indica que el texto sale del equipo hacia el proveedor elegido antes de empezar; la clave se trata como credencial (SUP-SEC01).
- **A6. Traducción aportada por el User** `[estado: ausente; propuesto]` (paso 4): el User pega o importa una traducción; el sistema la alinea con los segmentos y la registra con esa procedencia.
- **A7. Corregir** `[estado: ausente; propuesto]` (paso 5): el User edita segmentos traducidos; la edición crea una nueva revisión.

## Excepciones

- **E1. Proveedor inaccesible o sin crédito** `[estado: ausente; propuesto]` (paso 4): el job falla con la condición clasificada; los segmentos traducidos se conservan para reanudar.
- **E2. Par de idiomas no admitido** `[estado: ausente; propuesto]` (paso 1): el motor no admite el par; no se crea el job.

## Postcondiciones

- Existe una traducción registrada con su procedencia, o el job terminó con una condición clasificada.
- La entrada no cambió.

## Requisitos especiales

- No se exige repetir el reconocimiento de voz cuando ya existe una entrada textual válida.

## Reglas, requisitos y restricciones asociados

- [BR-55](../business-rules.md); SUP-SEC01, SUP-SEC07; UC-33, UC-36, UC-39.

## Criterios de aceptación

1. Una entrada temporizada conserva sus segmentos y marcas de tiempo.
2. Traducir subtítulos no ejecuta ninguna transcripción.
3. Con un motor local no se envía el texto fuera del equipo.
4. Editar un segmento no modifica la revisión anterior.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Motor y proveedor simulados: subtítulos, texto, selección y proveedor que falla | Desarrollo |
