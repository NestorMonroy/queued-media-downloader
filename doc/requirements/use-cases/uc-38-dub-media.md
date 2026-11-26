# UC-38: Doblar un medio

- **Objetivo:** el User obtiene una versión de un audio o un video con la voz en otro idioma, sincronizada con el original, usando las partes que ya tiene.
- **Actor principal:** User
- **Disparador:** el User pide doblar un medio a un idioma.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** sí: composición de operaciones con entradas existentes, resultados intermedios, recuperación por etapa y varios outputs (ADR-0035).
- **Estado:** aceptado (Responsable, instrucción 2.7.0): el objetivo y su flujo básico están en el alcance del producto. Los flujos alternativos y de excepción son propuestas (instrucciones 2.6.0 y 2.7.0) pendientes de aprobación: aceptar el objetivo no aprueba todos sus flujos, mecanismos, modelos ni runtimes. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (`dub_pipeline.py`, `dub_resume.py`, `incremental.py`, proyectos guardados). Objetivo aceptado en la instrucción 2.7.0.
- **Independencia:** Compone UC-33, UC-34, UC-36 y UC-37 cuando hacen falta; no es un diseñador genérico de flujos de trabajo.

## Breve descripción

El doblaje combina, según lo que ya exista, preparación del medio, transcripción, traducción, generación de voz, sincronización, mezcla y composición. No todas las etapas son obligatorias: el User puede aportar una transcripción, una traducción, unos subtítulos, una voz ya generada o sus propias pistas.

## Precondiciones

- UC-01 completado; los modelos o proveedores de las etapas que hagan falta están disponibles.

## Flujo básico

1. El User elige el medio, el idioma de destino, la voz y las entradas que ya tiene.
2. El sistema determina qué operaciones hacen falta y busca resultados reutilizables según BR-55.
3. El sistema obtiene el texto de destino: reutiliza la traducción, traduce una transcripción o subtítulos existentes, o transcribe y traduce.
4. El sistema genera la voz de cada segmento (UC-37), o usa la voz o las pistas aportadas.
5. El sistema sincroniza, mezcla la voz con el fondo si se pidió y compone el medio doblado.
6. El sistema publica el medio doblado como output nuevo, con reclamación, y conserva el original.

## Flujos alternativos

- **A1. Revisar antes de generar** `[estado: ausente; propuesto]` (paso 3): el User revisa y corrige la traducción; la corrección invalida solo los resultados posteriores de los segmentos afectados.
- **A2. Pistas del User** `[estado: ausente; propuesto]` (paso 4): el User aporta una pista de voz o de fondo; se valida y se usa con esa procedencia.
- **A3. Regenerar una parte** `[estado: ausente; propuesto]` (paso 4): el User cambia el texto, la voz o la sincronización de uno o varios segmentos; solo se rehacen esos segmentos y la composición.
- **A4. Cambiar una pista** `[estado: ausente; propuesto]` (paso 5): el User sustituye la pista de fondo o de voz; solo se repiten la mezcla y la composición.
- **A5. Exportar de nuevo** `[estado: ausente; propuesto]` (paso 6): el User pide otro formato o destino; se recompone sin repetir inferencias válidas.
- **A6. Reanudar tras un cierre** `[estado: ausente; propuesto]` (paso 3): las operaciones y los segmentos con evidencia válida no se repiten.
- **A7. Varios outputs** `[estado: ausente; propuesto]` (paso 6): el User pide además la pista de voz o los subtítulos; cada uno es un output del job (D-15).

## Excepciones

- **E1. Una operación falla** `[estado: ausente; propuesto]` (paso 3): el job falla en esa operación con la condición clasificada; las anteriores con evidencia válida se conservan para reanudar y nada se publica como completo.
- **E2. Recursos no disponibles** `[estado: ausente; propuesto]` (paso 4): la admisión aplaza la operación con el recurso concreto.

## Postcondiciones

- Existe un medio doblado registrado como output nuevo, o el job terminó con una condición clasificada en una operación identificada.
- El medio original no cambió.

## Requisitos especiales

- No se impone una secuencia única: la composición depende de las entradas disponibles (diseño, §18.3).

## Reglas, requisitos y restricciones asociados

- [BR-53](../business-rules.md), [BR-55](../business-rules.md); D-15; UC-33, UC-34, UC-36, UC-37, UC-39; diseño, §18.3.

## Criterios de aceptación

1. Con una traducción existente no se ejecuta ninguna transcripción ni traducción.
2. Un cierre a mitad no repite operaciones ni segmentos con evidencia válida.
3. Cambiar un segmento rehace solo ese segmento y la composición.
4. El original queda intacto y el doblaje es un output nuevo reclamado.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Motores simulados: entradas existentes, cierre a mitad, corrección parcial y cambio de pista | Desarrollo |
