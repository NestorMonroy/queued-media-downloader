# ADR-0035: Resultados derivados con identidad propia y composición de etapas

- **Estado:** Propuesta (instrucción 2.6.0). Se acepta cuando el Responsable apruebe el primer candidato de procesamiento (UC-33 a UC-38).
- **Fecha:** 2026-11-26
- **Relación:**
  - generaliza [ADR-0033](adr-0033-output-identity-and-storage-references.md) a operaciones que no son descargas;
  - conserva [ADR-0030](adr-0030-final-file-ownership-claims.md) y [ADR-0034](adr-0034-single-coordinator-and-isolated-execution.md);
  - análisis en el [diseño, Parte 3, §18.2 y §18.3](../design/03-target-architecture-and-evolution.md#182-identidad-de-los-resultados-derivados).

## Contexto

Las operaciones de la orientación estratégica (transcribir, traducir, resumir, generar subtítulos, generar voz, doblar) producen resultados a partir de otros resultados, con modelos y parámetros, y algunas son secuencias de etapas largas. VoiceStudio recupera un doblaje por segmento (`dub_resume.py`) y regenera solo los segmentos cuyas entradas cambiaron (`incremental.py`); escalona en privado y promueve al publicar.

## Decisión

1. Un resultado derivado tiene identidad propia, calculada a partir de las identidades de sus entradas, la operación, el modelo y su versión y los parámetros que afectan al resultado (BR-55, propuesta).
2. Una operación compuesta es una secuencia fija de etapas definida por la operación; cada etapa produce un resultado intermedio con identidad y evidencia propias.
3. La recuperación no repite etapas ni segmentos con evidencia verificada; lo publicado solo cambia al terminar.
4. Un resultado derivado nunca reemplaza su entrada; las entradas, los modelos y las cachés no se reclaman como outputs del job.

## Consecuencias

- Reutilización y detección de duplicados entre jobs de procesamiento.
- Sin diseñador genérico de flujos de trabajo.
- El registro de outputs necesitará referencias de entrada y de etapa (diseño de la migración cuando se autorice).

## Alternativas descartadas

- **Identidad solo por job:** impide reutilizar transcripciones entre jobs y recuperar por etapa.
- **Motor de flujos configurable:** sin necesidad identificada (análisis, §16.7).
