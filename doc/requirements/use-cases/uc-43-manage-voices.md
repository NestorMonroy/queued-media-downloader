# UC-43: Administrar voces

- **Objetivo:** el User mantiene voces reutilizables —predefinidas o diseñadas por atributos— para usarlas en la generación de voz y en el doblaje.
- **Actor principal:** User
- **Disparador:** el User quiere usar la misma voz en varias generaciones.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** no por sí solo: entidad referenciada por UC-37 y UC-38.
- **Estado:** candidato (propuesta de la instrucción 2.7.0, pendiente de aprobación del Responsable). Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio: tabla `voice_profiles` como entidad propia (nombre, idioma, instrucciones, tipo, receta de diseño, campos de consentimiento) referenciada por el historial de generación; borrar un proyecto no borra voces. [Análisis, §17.4](../requirements-analysis.md#174-proyectos-voces-regeneración-y-perfiles).
- **Independencia:** UC-37 genera audio con una voz; aquí se crean, consultan y eliminan voces. La clonación a partir de audio de referencia está fuera del dominio según la Visión; este candidato no la incluye y su revisión es una cuestión abierta del Responsable.

## Breve descripción

Una voz guarda su nombre, idioma, el motor y modelo con los que funciona y sus atributos de diseño. El User la elige en UC-37 y UC-38.

## Precondiciones

- Hay un modelo de voz utilizable (UC-39).

## Flujo básico

1. El User crea una voz eligiendo un modelo y sus atributos.
2. El sistema genera una muestra con la voz.
3. El User guarda la voz.
4. El User consulta sus voces y las elige en UC-37 o UC-38.

## Flujos alternativos

- **A1. Eliminar una voz** `[estado: ausente]` (paso 4): se elimina la voz; los audios ya generados con ella se conservan.
- **A2. Modelo no disponible** `[estado: ausente]` (paso 4): la voz se muestra como no utilizable hasta que su modelo vuelva a estar disponible.

## Excepciones

- **E1. Atributos no admitidos** `[estado: ausente]` (paso 1): el modelo no admite los atributos pedidos; la voz no se crea.

## Postcondiciones

- Las voces guardadas se pueden elegir en UC-37 y UC-38.

## Requisitos especiales

- Pendiente de aprobación: decidir si el objetivo se acepta como caso de uso o queda dentro de UC-37.

## Reglas, requisitos y restricciones asociados

- UC-37, UC-38, UC-39; Visión (clonación fuera del dominio).

## Criterios de aceptación

1. Eliminar una voz no elimina audios generados con ella.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Voces con un motor simulado | Desarrollo |
