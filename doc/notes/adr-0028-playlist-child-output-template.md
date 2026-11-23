# ADR-0028: Plantilla de salida de los hijos de una playlist

- **Estado:** Aceptada
- **Fecha:** 2026-11-23
- **Decisión pendiente que resuelve:** D3 del [plan de E2](../project-management/iteration-plan-e2.md#49-decisiones-pendientes-del-responsable)
- **Sustituye en parte:** el valor de `playlist_output_template` del [diseño, Parte 2](../design/02-flows-persistence-and-operations.md), que pasa a ser una regla y no un ajuste

## Contexto

Los jobs hijos de una playlist (UC-04) guardan su `PlaylistContext`: id, título, índice y, si se conoce, el número de entradas. La plantilla de salida se construye con ese contexto, sin volver a extraer la playlist ni usar `extra_info` ([ADR-0009](adr-0009-playlist-expansion-into-jobs.md)). Quedaban abiertos el nombre de la carpeta, el relleno del índice, la longitud y las playlists anidadas.

Lo que hace yt-dlp 2026.10.26:

- Sus ejemplos usan `-o "%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s"`. El campo `playlist` es el título de la playlist o, sin título, su id (`_playlist_infodict`). Para las playlists de un canal propone `%(uploader)s/%(playlist)s/…`: una carpeta por la playlist inmediata.
- `playlist_index` se rellena con ceros hasta las cifras del último índice. Con `lazy_playlist`, que es como recorre las entradas la expansión del proyecto, ese índice no se conoce y no se rellena.
- Cada campo pasa por `sanitize_filename` (`/` → `⧸`, `?` → `？`, …). En Windows, `sanitize_path` sustituye además un punto o un espacio final.
- `trim_file_name` recorta solo el nombre del archivo, no las carpetas.

## Decisión

**La plantilla del ejemplo de yt-dlp, construida por el proyecto con el contexto guardado:**

```text
<playlist>/<playlist_index> - <plantilla del job>
```

- **Carpeta:** el título de la playlist o, sin título, su id, saneado con `sanitize_filename` de yt-dlp y con `%` escapado.
- **Índice:** relleno con ceros hasta las cifras del número de entradas que declara el sitio (`playlist_count`, que YouTube trae con `process=False`). Si no lo declara, sin relleno, como `lazy_playlist`. Si el índice supera ese número, se trata como desconocido.
- **Nombre del archivo:** la plantilla que el job guardó al encolar (`single_media_output_template`). No hay un ajuste propio para las playlists.
- **Longitud:** la carpeta se recorta a `max_filename_length`, el mismo valor que yt-dlp aplica al nombre del archivo. Es la única extensión respecto a yt-dlp, para no rebasar los límites de ruta de Windows.
- **Anidadas:** una sola carpeta, la de la playlist inmediata. Un video de una pestaña de canal va en la carpeta de la pestaña.

Ejemplo con una playlist de YouTube de 12 entradas:

```text
downloads\Lo-fi beats\03 - First song [abc123].webm
downloads\audio\Lo-fi beats\03 - First song [abc123].opus
```

## Consecuencias

- Los archivos se nombran como los nombraría yt-dlp con su ejemplo, incluido el saneado, de modo que quien conozca yt-dlp los reconoce.
- Dos playlists distintas con el mismo título comparten carpeta. Los nombres de archivo llevan el id del contenido, así que no se pisan.
- Sin el número de entradas, los índices no se rellenan. El Explorador de Windows ordena los números de forma natural, así que el orden se mantiene.
- Un título que sea un nombre reservado de Windows (`CON`, `NUL`, …) no se trata, igual que en yt-dlp.
- Un video que está en dos listas se descarga una vez, en la carpeta del primer job que lo encuentra; la otra copia queda `SKIPPED` (UC-04 A2). Con varios workers, cuál llega primero depende del orden de ejecución (hallado en T30).
