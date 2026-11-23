# ADR-0011: Convenciones de código

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Nota:** los pendientes de herramientas e idioma de los comentarios se resuelven en [ADR-0019](adr-0019-code-quality-tools.md).

## Contexto

El equipo se comunica en español, pero el ecosistema (Python, yt-dlp, librerías) está en inglés. Hace falta una regla clara de idioma y unos criterios de calidad comunes antes de escribir código.

## Decisión

**Idioma:**
- **En inglés:** nombres de archivos y carpetas, módulos, clases, funciones, métodos, atributos, parámetros, variables y cualquier otro identificador.
- **En inglés:** mensajes al usuario (salida de la CLI) y mensajes de log *(resuelto el 2026-11-22)*.
- **En español:** docstrings.

**Referencias obligatorias** *(añadido el 2026-11-22)*:
- [Guías de clean code](../reference/clean-code-guidelines/README.md): principios, prácticas y patrones.
- [Principios de nombres](../reference/naming-principles/clean-code-naming-principles.md).
- [Vocabulario del proyecto](../design/00-vocabulary.md): una palabra por concepto ([ADR-0014](adr-0014-use-case-structure-and-vocabulary.md)).

Los nombres se revisan contra estas referencias **antes** de proponerlos, no después.

**Calidad:**
- **Clean code:** nombres descriptivos, funciones pequeñas con una sola responsabilidad, sin números ni cadenas mágicas, sin código duplicado.
- **Diseño modular:** módulos separados por responsabilidad (cola, persistencia, workers, resolución de ffmpeg, integración con yt-dlp, CLI), que se comunican mediante interfaces y no dependen de detalles internos de otros módulos.

## Consecuencias

- Los nombres de archivo de esta documentación también siguen la regla (`adr-0011-code-conventions.md`); su contenido está en español.
- Las interfaces definidas en otras decisiones (worker en [ADR-0008](adr-0008-process-based-worker-pool.md), resolución de ffmpeg en [ADR-0006](adr-0006-ffmpeg-resolution-and-verification.md)) son la base del diseño modular.

## Pendiente de definir

- Idioma de los comentarios en línea.
- Herramientas que hagan cumplir las convenciones (formateador, linter, anotaciones de tipo, verificador de tipos). *El linter de importaciones (`import-linter`) quedó decidido en [ADR-0017](adr-0017-ffmpeg-inspired-public-api-and-dependency-graph.md).*
