# UC-40: Administrar colecciones de medios

- **Objetivo:** el User agrupa contenidos —remotos, locales, resultados y pendientes de obtener— en colecciones con nombre y orden, sin tener que descargarlos para organizarlos.
- **Actor principal:** User
- **Disparador:** el User quiere organizar contenidos por tema, curso o proyecto.
- **Prioridad:** baja.
- **Significativo para la arquitectura:** sí, moderadamente: una colección guarda referencias a elementos de naturalezas distintas, cuya representación persistente se elige después de definir sus relaciones (diseño, §18.2).
- **Estado:** aceptado (Responsable, instrucción 2.7.0): el objetivo y su flujo básico están en el alcance del producto. Los flujos alternativos y de excepción son propuestas (instrucciones 2.6.0 y 2.7.0) pendientes de aprobación: aceptar el objetivo no aprueba todos sus flujos, mecanismos, modelos ni runtimes. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** Listas locales de NewPipe; exportación M3U de UC-25 A10. Objetivo aceptado en la instrucción 2.7.0.
- **Independencia:** Distinta de una playlist remota (UC-04), de una suscripción de contenido (UC-30), de un lote de descarga (una petición de UC-02), de la cola de jobs (UC-14), del historial de descargas y de un proyecto de procesamiento (UC-42, candidato).

## Breve descripción

Una colección es una lista ordenada de referencias. Un elemento puede ser un medio remoto identificado, un medio local, un resultado descargado, una transcripción, unos subtítulos, un resumen, un audio generado, un doblaje o un contenido pendiente de obtener. Administrar la colección no mueve, copia ni borra archivos.

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User crea una colección con un nombre.
2. El User añade elementos.
3. El sistema guarda las referencias en orden.
4. El User consulta la colección con el estado de cada elemento.

## Flujos alternativos

- **A1. Añadir un medio remoto sin obtenerlo** `[estado: ausente; propuesto]` (paso 2): se guarda su identidad de contenido; el User puede obtenerlo después con UC-02.
- **A2. Obtener los pendientes** `[estado: ausente; propuesto]` (paso 4): el User pide obtener los elementos remotos de la colección; se encolan con UC-02.
- **A3. Reordenar o quitar** `[estado: ausente; propuesto]` (paso 4): solo cambian las referencias.
- **A4. Elemento no disponible** `[estado: ausente; propuesto]` (paso 4): el elemento se eliminó o se movió; se muestra como no disponible y no se elimina solo.
- **A5. Exportar** `[estado: ausente; propuesto]` (paso 4): se exporta como lista (M3U o el formato de UC-22) sin secretos (SUP-SEC07).
- **A6. Eliminar la colección** `[estado: ausente; propuesto]` (paso 4): se eliminan sus referencias y nada más.

## Excepciones

- **E1. Nombre repetido** `[estado: ausente; propuesto]` (paso 1): el sistema pide otro nombre.

## Postcondiciones

- Las colecciones reflejan las referencias del User; ningún archivo se movió, copió ni borró por administrarlas.

## Requisitos especiales

- Una colección no exige conservar indefinidamente información de un contenido que ya no se necesita: quitar un elemento quita su referencia.

## Reglas, requisitos y restricciones asociados

- [BR-52](../business-rules.md); SUP-SEC07; UC-02, UC-22, UC-25.

## Criterios de aceptación

1. Eliminar una colección no toca ningún archivo.
2. Un medio remoto puede organizarse sin obtenerlo.
3. Un elemento que desaparece se muestra como no disponible.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Colecciones con elementos remotos, locales y derivados que desaparecen | Cualquier sistema |
