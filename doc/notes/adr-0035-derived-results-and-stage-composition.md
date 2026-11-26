# ADR-0035: Resultados derivados con identidad propia y composición de operaciones

- **Estado:** Orientación aceptada (instrucción 2.7.0, §46 y §55); detalles de realización pendientes de cualificación. Propuesta en la 2.6.0.
- **Fecha:** 2026-11-26 (reconciliado en la instrucción 2.7.0).
- **Relación:**
  - generaliza [ADR-0033](adr-0033-output-identity-and-storage-references.md) a operaciones que no son descargas;
  - conserva [ADR-0030](adr-0030-final-file-ownership-claims.md) y [ADR-0034](adr-0034-single-coordinator-and-isolated-execution.md);
  - análisis en el [diseño, Parte 3, §18.2 y §18.3](../design/03-target-architecture-and-evolution.md#182-identidades-y-resultados-derivados) y en BR-55.

## Contexto

Las operaciones aceptadas (UC-33 a UC-38) producen resultados a partir de otros resultados, con modelos y parámetros, y algunas componen varias operaciones. Los modelos generativos no garantizan el mismo resultado para la misma petición. VoiceStudio recupera un doblaje por segmento y regenera solo los segmentos cuyas entradas cambiaron.

## Decisión

**Aceptado (orientación):**
1. Se representan entradas, operaciones, ejecuciones, resultados, resultados intermedios, dependencias, configuración efectiva y modelos, sin un marco general de flujos de trabajo.
2. Identidades independientes: contenido, petición (portable y local), job, especificación de procesamiento, ejecución, output, resumen del contenido y referencia de almacenamiento. No se usa un único identificador para todas, ni se crean identificadores persistentes nuevos donde los existentes bastan.
3. Igualdad de petición no implica igualdad binaria; la reutilización exige las condiciones de BR-55.
4. La composición depende de las entradas disponibles: secuencias, dependencias, ramificaciones, resultados opcionales, entradas existentes y reutilización. No todas las peticiones ejecutan todas las operaciones.
5. Artefactos temporales, de recuperación, resultados intermedios, outputs publicados y resultados invalidados tienen ciclos de vida distintos (diseño, §18.3). Nunca se publica como definitivo un resultado incompleto.

**Pendiente de cualificación:**
- qué atributos de la especificación afectan al resultado en cada operación;
- la representación persistente de la especificación y de la ejecución;
- dónde vive la evidencia de recuperación de cada operación y cómo se verifica;
- la elección entre operaciones independientes, etapas internas o peticiones compuestas (recomendación en el diseño, §18.3, no aprobada).

## Consecuencias

- La identidad de U3 no debe suponer que todo job es una descarga (plan de E3, §12.3).
- No se declara cualificado ningún contrato que dependa de experimentos o decisiones funcionales no resueltas.

## Alternativas descartadas

- **Identidad solo por job:** impide reutilizar resultados entre jobs y recuperar por operación.
- **Motor de flujos configurable, lenguaje de flujos u orquestador:** sin necesidad identificada.
- **Secuencia fija de etapas** (versión de la 2.6.0): imponía operaciones innecesarias cuando el User ya tiene una entrada.
