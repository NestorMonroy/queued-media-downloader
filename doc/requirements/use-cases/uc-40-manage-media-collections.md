# UC-40: Administrar colecciones de medios

- **Objetivo:** el User agrupa sus resultados en colecciones con nombre (por tema, curso o proyecto) y las consulta, ordena y exporta sin mover los archivos.
- **Actor principal:** User
- **Disparador:** el User quiere organizar resultados más allá de la carpeta de descargas.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** no: referencias a outputs registrados; no cambia la propiedad ni la ubicación.
- **Estado:** candidato (propuesta de la instrucción 2.6.0, pendiente de aprobación del Responsable). Horizonte: futuro. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** Listas de reproducción locales de NewPipe y GreenTuber, y exportación M3U de UC-25 A10 (§15). Objetivo de organización de la orientación estratégica (D-23). Evidencia y nivel en el [análisis de requisitos, §16](../requirements-analysis.md#16-descubrimiento-260-ia-privacidad-y-modelo-comercial).
- **Independencia:** UC-25 administra cada resultado; aquí se agrupan referencias. Una colección no es una playlist del sitio (UC-04).

## Breve descripción

Una colección es una lista ordenada de referencias a outputs registrados. Añadir, quitar o reordenar no mueve, copia ni borra archivos.

## Precondiciones

- Existen resultados registrados (UC-25).

## Flujo básico

1. El User crea una colección con un nombre.
2. El User añade resultados a la colección.
3. El sistema guarda las referencias en orden.
4. El User consulta la colección con el estado de cada resultado.

## Flujos alternativos

- **A1. Reordenar o quitar** `[estado: ausente]` (paso 3): solo cambian las referencias.
- **A2. Resultado eliminado o movido** `[estado: ausente]` (paso 4): la referencia se muestra como no disponible; no se elimina sola.
- **A3. Exportar la colección** `[estado: ausente]` (paso 4): se exporta como lista (M3U o el formato de UC-22) sin secretos (SUP-SEC07).

## Excepciones

- **E1. Nombre repetido** `[estado: ausente]` (paso 1): el sistema pide otro nombre.

## Postcondiciones

- Las colecciones reflejan las referencias del User; ningún archivo se movió, copió ni borró por administrarlas.

## Requisitos especiales

- Eliminar una colección no elimina resultados.

## Reglas, requisitos y restricciones asociados

- [BR-52](../business-rules.md); SUP-SEC07; UC-22, UC-25.

## Criterios de aceptación

1. Eliminar una colección no toca ningún archivo.
2. Un resultado eliminado aparece como no disponible en sus colecciones.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Ciclo de vida de colecciones con resultados que desaparecen | Cualquier sistema |
