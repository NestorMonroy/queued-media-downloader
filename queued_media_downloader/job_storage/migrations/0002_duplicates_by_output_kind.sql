-- La regla de duplicados compara el contenido y el tipo de archivo de salida
-- (ADR-0012, seguimiento de T21): el mismo contenido como video y como solo
-- audio son dos archivos distintos. audio_only ya se guarda en
-- download_options, así que el índice lo lee de ahí en lugar de duplicarlo.
DROP INDEX unique_active_download_per_media;

CREATE UNIQUE INDEX unique_active_download_per_media
    ON jobs (extractor_key, media_id, json_extract(download_options, '$.audio_only'))
    WHERE kind = 'DOWNLOAD' AND media_id IS NOT NULL AND status <> 'SKIPPED';
