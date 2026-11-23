# ADR-0021: TDD y validación en Windows sin integración continua

- **Estado:** Aceptada
- **Fecha:** 2026-11-23

## Contexto

Varios riesgos dependen de Windows (spawn de procesos, Job Object, rutas, binarios de ffmpeg). Se evaluó validarlos con GitHub Actions (`windows-latest`), como hace yt-dlp en su workflow `core.yml`. yt-dlp-gui, en cambio, no tiene pruebas: su único workflow compila el ejecutable.

Se descarta GitHub Actions para no acoplar el proyecto a un proveedor. Hace falta otra forma de validar el comportamiento en Windows.

Gran parte del comportamiento de Windows se puede probar en cualquier sistema:
- `multiprocessing.get_context("spawn")` reproduce en Linux el mecanismo de creación de procesos que Windows usa por defecto.
- `pathlib.PureWindowsPath` aplica las reglas de rutas de Windows sin ejecutarse en Windows.
- La lógica de cancelación se prueba con `FakeProcessTreeTerminator` ([ADR-0013](adr-0013-process-tree-terminator-abstraction.md)).

Solo dos comportamientos requieren Windows real: que el Job Object termine de verdad el árbol de procesos, y que `ffmpeg.exe` y `ffprobe.exe` del repositorio arranquen con sus DLL.

## Decisión

1. **TDD** como práctica de desarrollo: prueba primero, código mínimo, refactorización.
2. **Adaptadores mínimos** (*humble object*): el código específico de Windows se reduce al mínimo; toda la lógica que pueda separarse se prueba en cualquier sistema.
3. **Dos conjuntos de pruebas**, diferenciados por marcadores de pytest:
   - `uv run pytest`: todo lo independiente de la plataforma. Es el ciclo diario de TDD.
   - `uv run pytest -m windows`: las pruebas que requieren Windows real.
4. **Sin servidor de integración continua.** Las pruebas `windows` se ejecutan en un entorno Windows **al cerrar cada iteración** (evaluación de la iteración de RUP) y antes de cada entrega. Hay un entorno Windows disponible para ese paso.
5. **Pruebas de descarga sin internet:** servidor HTTP local con medios generados con ffmpeg, como hace yt-dlp. Las descargas reales de YouTube son verificaciones manuales, no pruebas automatizadas.

## Consecuencias

- Las pruebas no dependen de ningún proveedor: si en el futuro se quiere CI, basta con que ejecute los mismos comandos (#10, las herramientas son plugins).
- Un error específico de Windows puede detectarse con retraso, hasta el cierre de la iteración. El riesgo se limita manteniendo mínimos los adaptadores de Windows.
- La memoria consumida (RSS) se mide en el entorno Windows al cerrar cada iteración; los tiempos no se usan como criterio, porque dependen del equipo.
- El antivirus y los archivos `.part` se verifican manualmente: no es un comportamiento reproducible de forma determinista.
