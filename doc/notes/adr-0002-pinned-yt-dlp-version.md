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

## Seguimiento: actualización a 2026.11.23 (2026-11-26)

La validación en Windows (T42-D3) encontró que el solucionador de retos de yt-dlp-ejs fallaba con la variante `main` del reproductor de YouTube, la predeterminada de 2026.10.26. Siguiendo el [procedimiento de actualización](../process/yt-dlp-update-procedure.md), se fija **yt-dlp 2026.11.23**, que usa la variante `tv` por defecto (yt-dlp #18124) con la misma yt-dlp-ejs 0.8.0 y deno 2.9.8. Los módulos de los que dependen los contratos del proyecto son idénticos a los de 2026.10.26. Las referencias a 2026.10.26 en los ADR y documentos anteriores describen los hallazgos de su fecha y se conservan.
