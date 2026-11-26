# UC-15: Consultar un contenido antes de encolarlo

- **Objetivo:** el User sabe qué contiene una URL (título, duración, formatos y calidades disponibles; si es una playlist, cuántas entradas tiene) para decidir qué y cómo encolar, sin descargar nada y sin tocar la cola.
- **Actor principal:** User
- **Actor secundario:** Media site
- **Disparador:** el User tiene una URL y no sabe qué formato pedir, si es una playlist o cuánto ocupa.
- **Prioridad:** media
- **Significativo para la arquitectura:** no (reutiliza la extracción de `media_extraction`; es el único comando de consulta que accede a la red)
- **Estado:** propuesto; **no implementado**.
- **Origen:**
  - **Seal:** obtiene la información y elige el formato antes de descargar (`DownloaderV2.fetchInfo`, `ui/page/downloadv2/configure/FormatPage.kt`, `PlaylistSelectionPage.kt`).
  - **Kannagi:** el botón Analyze (`--dump-json` en `Wrappers/DLP.cs`; listas de formatos, subtítulos y capítulos en `ViewModels/Main.cs`).
  - **yt-dlp:** `-F` (`--list-formats`), `--dump-json`, `--simulate`.

## Breve descripción

`inspect URL` extrae la información con yt-dlp, igual que la primera fase de una descarga, pero no descarga ni crea jobs. La salida orienta las opciones de `enqueue` (UC-02): el format selector, `--audio-only`, `--playlist` y la selección de entradas (UC-02 A6).

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader inspect URL`.
2. El sistema valida la URL, como en UC-02.
3. El sistema extrae la información del contenido con yt-dlp, sin descargar.
4. El sistema muestra:
   - el título, la duración y el sitio;
   - los formatos disponibles: id, contenedor, resolución, códecs y tamaño estimado;
   - el formato que elegiría el format selector configurado.
5. El sistema termina con código `0`. La cola no cambia.

## Flujos alternativos

- **A1. La URL es una playlist o un canal** (paso 3): extracción plana, la misma de UC-04. Muestra el título y el número de entradas si el sitio lo declara, y como mucho las primeras `N` entradas, sin resolverlas (ADR-0009).
- **A2. Enlace a un video dentro de una lista** (paso 3): muestra el video y avisa de que `--playlist` encolaría la lista entera (ADR-0027).
- **A3. `--format SELECTOR`** (paso 4): muestra qué formatos elegiría ese selector, sin descargar.
- **A4. Subtítulos disponibles** (paso 4): lista sus idiomas, si se aprueba la opción de subtítulos (UC-02 A7).

## Excepciones

- **E1. URL no válida:** como UC-02 A1; código `2`.
- **E2. Fallo de extracción:** se informa con el motivo y su indicación de qué hacer ([catálogo de condiciones de fallo](../failure-conditions.md)); código `1`.
- **E3. Restricción del sitio o corte de conectividad:** se informa como en UC-11, pero no hay jobs que aplazar; código `1`.

## Garantías

- **De éxito:** la información del contenido mostrada; la cola, las descargas y las reclamaciones, intactas.
- **Mínima:** no se escribe nada en la cola ni en la carpeta de descargas.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-01, BR-02 (cuenta como una petición al sitio) y BR-05.
- **Requisitos suplementarios:** SUP-F01 y SUP-U01.
- **Restricción:** a diferencia de `enqueue` (UC-02, que no accede a la red), `inspect` sí accede a la red.
- **Dependencias:** UC-02 y UC-04.

## Criterios de aceptación

1. `inspect` nunca crea jobs ni escribe en la carpeta de descargas.
2. Los formatos mostrados son los que yt-dlp ofrecería al descargar con las mismas opciones.
3. Con una playlist, la memoria no crece con el número de entradas (SUP-P02).

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Video, playlist y enlace a un video dentro de una lista, contra el servidor local | Cualquier sistema |
| Formatos y selección de un selector, con un manifiesto DASH local | Cualquier sistema |
| Video real de YouTube | **Windows**, campaña (`network`) |
