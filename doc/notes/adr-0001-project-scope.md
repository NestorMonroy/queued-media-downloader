# ADR-0001: Alcance inicial — cola de descargas sin GUI

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Nota:** el proyecto y su paquete se llaman `queued-media-downloader` / `queued_media_downloader` desde [ADR-0015](adr-0015-project-and-package-name.md).

## Contexto

El proyecto se llama *yt-dlp-gui-clone*, pero en la etapa de análisis se separó el motor de la interfaz. Se evaluaron tres alcances: descarga simple, cola con varias descargas y GUI completa.

## Opciones consideradas

1. **Descarga simple:** una URL por ejecución. Insuficiente para playlists y para uso continuado.
2. **Cola con varias descargas:** motor reutilizable que gestiona trabajos, progreso, cancelación y reanudación.
3. **GUI completa:** interfaz gráfica además del motor.

## Decisión

El alcance inicial es una **cola con varias descargas, sin GUI**. El proyecto usa yt-dlp como librería de Python, no como ejecutable externo.

## Consecuencias

- La interacción inicial es por línea de comandos (CLI).
- El motor debe diseñarse para que una GUI futura lo consuma sin cambios: eventos de progreso, comandos de cancelación y estado persistente expuestos por interfaces, no por salida de consola.
- Las decisiones de concurrencia ([ADR-0008](adr-0008-process-based-worker-pool.md)), playlists ([ADR-0009](adr-0009-playlist-expansion-into-jobs.md)) y persistencia ([ADR-0010](adr-0010-sqlite-persistent-queue.md)) derivan de este alcance.
