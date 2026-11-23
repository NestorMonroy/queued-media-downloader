# ADR-0002: Versión de yt-dlp fijada

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto

yt-dlp publica versiones con fecha (sin versionado semántico) y su README advierte que el canal `stable` se queda atrás frente a los cambios de los sitios. Como librería, su API (parámetros de `YoutubeDL`, campos de los hooks) no tiene garantías de compatibilidad entre versiones.

## Opciones consideradas

1. **Versión al día:** siempre funciona con los sitios, pero el contrato con la librería puede cambiar sin aviso.
2. **Versión fijada:** contrato estable y reproducible; se rompe cuando un sitio cambia hasta que se actualiza a propósito.

## Decisión

Se fija **yt-dlp 2026.10.26**. La actualización es un procedimiento explícito: cambiar la versión, probar y publicar.

## Consecuencias

- El contrato con la librería (parámetros, hooks, excepciones) se analiza y prueba contra una versión concreta.
- Los errores de extractor deben comunicarse con claridad, indicando que puede hacer falta actualizar yt-dlp.
- Hay que documentar el procedimiento de actualización.
- La fijación de dependencias transitivas la resuelve `uv.lock` ([ADR-0003](adr-0003-packaging-with-uv-and-pyproject.md)).
