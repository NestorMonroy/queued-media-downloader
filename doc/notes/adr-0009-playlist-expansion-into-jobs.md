# ADR-0009: Expansión de playlists en trabajos individuales

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Nota:** el uso de `download_archive` queda descartado por [ADR-0012](adr-0012-no-download-archive-no-database-triggers.md); los términos vigentes están en [ADR-0014](adr-0014-use-case-structure-and-vocabulary.md).

## Contexto

Una URL de playlist o canal puede tratarse como un solo trabajo o expandirse en un trabajo por video. Hallazgos en el código de yt-dlp 2026.10.26:
- En `__process_playlist`, con el valor por defecto de la API (`extract_flat=False`), yt-dlp mantiene en memoria la información completa de todos los videos de la playlist.
- Con `extract_flat='in_playlist'`, cada entrada trae ya `playlist_index`, `playlist_title`, `playlist_id`, `n_entries`, etc. (`_playlist_infodict`).
- `extract_info` acepta `extra_info`, pero está documentado como *"For internal use only"*.

## Opciones consideradas

1. **Un trabajo por playlist:** simple, pero con progreso y cancelación globales, reintento de toda la playlist y memoria que crece con su tamaño.
2. **Expansión en N trabajos:** cada video es visible, cancelable y reintentable; memoria acotada por trabajo.

## Decisión

Modelo de **dos tipos de trabajo** que comparten cola, pool y tabla de estados:

```
Trabajo de expansión (URL de playlist o canal)
   └─ genera N → Trabajos de descarga (un video cada uno)
```

- La expansión usa `extract_info(url, download=False)` con `extract_flat='in_playlist'` y guarda el contexto de la playlist de cada entrada en SQLite.
- El contexto se recupera **construyendo el `outtmpl` de cada trabajo** con esos valores insertados como texto (escapando `%` y saneando el nombre). No se usa `extra_info`.

## Consecuencias

Casos límite que la expansión debe resolver:
- **Playlists anidadas** (canal → pestañas → playlists): una expansión puede generar otras expansiones.
- **`multi_video`:** no se expande; es un único trabajo.
- **Entradas no disponibles:** se registran como trabajos omitidos, no como errores.
- **Duplicados:** restricción única por `(extractor_key, id)` en SQLite, además de `download_archive`.
- **Canales grandes:** la expansión es un trabajo con progreso y cancelación propios, e inserta en SQLite por lotes.
- Cancelar una playlist equivale a cancelar su expansión y sus trabajos hijos.
