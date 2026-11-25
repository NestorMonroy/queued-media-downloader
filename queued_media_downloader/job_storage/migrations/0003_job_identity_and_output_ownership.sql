-- Identidad y propiedad de los archivos de cada job (T44, riesgo R-14).
--
-- 1. AUTOINCREMENT: SQLite no vuelve a dar el id de un job borrado (purge,
--    UC-10). La carpeta de parciales de un job se nombra con su id, así que un
--    id reutilizado heredaría los parciales de otro job.
-- 2. unique_output_path: dos jobs no pueden reclamar el mismo archivo final.
--    Si una plantilla sin %(id)s o un título recortado dan el mismo nombre a
--    dos contenidos, yt-dlp toma el segundo por "ya descargado"; el índice
--    impide que ese job quede COMPLETED con el archivo de otro.
--
-- SQLite no admite añadir AUTOINCREMENT con ALTER TABLE: se reconstruyen las
-- tablas. Con foreign_keys activo, DROP TABLE ejecuta las acciones ON DELETE
-- CASCADE, y el PRAGMA no se puede cambiar dentro de la transacción de la
-- migración. Por eso las tablas nuevas se refieren a sí mismas con su nombre
-- nuevo (jobs_new), se borran las antiguas sin que nada nuevo dependa de ellas,
-- y ALTER TABLE RENAME actualiza las referencias al renombrar.

CREATE TABLE jobs_new (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    kind                 TEXT    NOT NULL CHECK (kind IN ('EXPANSION', 'DOWNLOAD')),
    status               TEXT    NOT NULL CHECK (status IN (
                             'PENDING', 'RUNNING', 'CANCELLATION_REQUESTED',
                             'COMPLETED', 'FAILED', 'CANCELLED', 'SKIPPED')),
    url                  TEXT    NOT NULL,
    parent_id            INTEGER REFERENCES jobs_new (id) ON DELETE CASCADE,
    extractor_key        TEXT,
    media_id             TEXT,
    title                TEXT,
    selected_format_id   TEXT,
    playlist_id          TEXT,
    playlist_title       TEXT,
    playlist_index       INTEGER,
    playlist_entry_count INTEGER,
    download_options     TEXT    NOT NULL,
    output_path          TEXT,
    attempt_count        INTEGER NOT NULL DEFAULT 0,
    failure_reason       TEXT,
    failure_message      TEXT,
    created_at           TEXT    NOT NULL,
    updated_at           TEXT    NOT NULL,
    started_at           TEXT,
    finished_at          TEXT
);

CREATE TABLE job_requests_new (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id       INTEGER NOT NULL REFERENCES jobs_new (id) ON DELETE CASCADE,
    request_type TEXT    NOT NULL CHECK (request_type IN ('CANCEL', 'RETRY')),
    requested_at TEXT    NOT NULL,
    processed_at TEXT
);

INSERT INTO jobs_new SELECT * FROM jobs;

INSERT INTO job_requests_new SELECT * FROM job_requests;

-- Los ids más altos no deben volver a usarse aunque se borren después.
INSERT INTO sqlite_sequence (name, seq)
    SELECT 'jobs_new', coalesce(max(id), 0) FROM jobs_new;

INSERT INTO sqlite_sequence (name, seq)
    SELECT 'job_requests_new', coalesce(max(id), 0) FROM job_requests_new;

DROP TABLE job_requests;

DROP TABLE jobs;

ALTER TABLE jobs_new RENAME TO jobs;

ALTER TABLE job_requests_new RENAME TO job_requests;

CREATE INDEX jobs_by_status ON jobs (status, id);

CREATE INDEX jobs_by_parent ON jobs (parent_id);

CREATE UNIQUE INDEX unique_active_download_per_media
    ON jobs (extractor_key, media_id, json_extract(download_options, '$.audio_only'))
    WHERE kind = 'DOWNLOAD' AND media_id IS NOT NULL AND status <> 'SKIPPED';

CREATE UNIQUE INDEX unique_output_path ON jobs (output_path)
    WHERE output_path IS NOT NULL;

CREATE INDEX unprocessed_job_requests ON job_requests (id) WHERE processed_at IS NULL;
