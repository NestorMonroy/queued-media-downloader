-- Esquema inicial de la cola (diseño, Parte 2, §2.2).
CREATE TABLE jobs (
    id                   INTEGER PRIMARY KEY,
    kind                 TEXT    NOT NULL CHECK (kind IN ('EXPANSION', 'DOWNLOAD')),
    status               TEXT    NOT NULL CHECK (status IN (
                             'PENDING', 'RUNNING', 'CANCELLATION_REQUESTED',
                             'COMPLETED', 'FAILED', 'CANCELLED', 'SKIPPED')),
    url                  TEXT    NOT NULL,
    parent_id            INTEGER REFERENCES jobs (id) ON DELETE CASCADE,
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

CREATE INDEX jobs_by_status ON jobs (status, id);

CREATE INDEX jobs_by_parent ON jobs (parent_id);

CREATE UNIQUE INDEX unique_active_download_per_media
    ON jobs (extractor_key, media_id)
    WHERE kind = 'DOWNLOAD' AND media_id IS NOT NULL AND status <> 'SKIPPED';

CREATE TABLE job_requests (
    id           INTEGER PRIMARY KEY,
    job_id       INTEGER NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    request_type TEXT    NOT NULL CHECK (request_type IN ('CANCEL', 'RETRY')),
    requested_at TEXT    NOT NULL,
    processed_at TEXT
);

CREATE INDEX unprocessed_job_requests ON job_requests (id) WHERE processed_at IS NULL;
