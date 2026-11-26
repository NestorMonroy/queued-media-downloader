# UC-42: Administrar proyectos de procesamiento

- **Objetivo:** el User guarda el contexto de un trabajo de procesamiento —entradas, preferencias, transcripciones y traducciones editadas, segmentos, voz elegida y pistas— para continuarlo, revisarlo y volver a ejecutarlo más tarde.
- **Actor principal:** User
- **Disparador:** el User prepara un doblaje u otro procesamiento en varias sesiones.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** sí: un proyecto es una entidad persistente distinta del job, de la colección y del output (diseño, §18.2).
- **Estado:** candidato (propuesta de la instrucción 2.7.0, pendiente de aprobación del Responsable). Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio: tabla `studio_projects` con estado editable y glosario por proyecto, distinta de `jobs` y de `dub_history`; borrar un proyecto no borra medios, voces ni audio generado; `project_bundle.py`: intercambio versionado de proyectos sin credenciales, pesos ni rutas absolutas. VoiceBlueprintPro endurece la validación de ese intercambio. [Análisis, §17.4](../requirements-analysis.md#174-proyectos-voces-regeneración-y-perfiles).
- **Independencia:** Un job es una ejecución; una colección agrupa contenido; un output es un resultado; un proyecto conserva el borrador y las decisiones entre ejecuciones. Guardar un proyecto no es conservar un job terminado.

## Breve descripción

El proyecto guarda referencias a sus entradas y resultados, los borradores editables (transcripción, traducción, segmentos), las preferencias y las ejecuciones realizadas. Puede ejecutarse de nuevo sin repetir lo que sigue siendo válido.

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User crea un proyecto con un nombre y sus entradas.
2. El User edita borradores y elige preferencias.
3. El sistema guarda el proyecto.
4. El User reabre el proyecto y continúa.
5. El User ejecuta el procesamiento desde el proyecto; cada ejecución es un job enlazado al proyecto.

## Flujos alternativos

- **A1. Eliminar el proyecto** `[estado: ausente]` (paso 4): se elimina el proyecto y sus borradores; las entradas, los outputs y las voces se conservan.
- **A2. Exportar e importar** `[estado: ausente]` (paso 3): el proyecto se intercambia sin credenciales, pesos de modelos ni rutas absolutas; al importarlo recibe identidades nuevas.

## Excepciones

- **E1. Entrada no disponible** `[estado: ausente]` (paso 4): una entrada se movió o eliminó; el proyecto lo indica y no se ejecuta hasta resolverla.

## Postcondiciones

- El proyecto conserva sus borradores y sus referencias; ningún archivo se borró por guardarlo o eliminarlo.

## Requisitos especiales

- Pendiente de aprobación: decidir si el objetivo se acepta como caso de uso o se cubre con UC-38 y UC-40.

## Reglas, requisitos y restricciones asociados

- UC-33, UC-34, UC-37, UC-38, UC-40; ADR-0035 (orientación aceptada).

## Criterios de aceptación

1. Eliminar un proyecto no elimina entradas, outputs ni voces.
2. Reabrir un proyecto recupera sus borradores.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Proyecto con borradores, ejecución y eliminación | Desarrollo |
