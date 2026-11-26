-- Propiedad sin decidir de un archivo final reclamado por varios jobs (R-14).
--
-- La migración 0003, tal como se publicó, daba un archivo que reclamaban dos o
-- más jobs de E1 al de id menor y pasaba los demás a FAILED. El id menor no
-- prueba quién escribió el archivo: con yt-dlp, un job posterior pudo tomarlo
-- por "ya descargado" o sobrescribirlo (FFmpegExtractAudio). Los datos
-- guardados no permiten saberlo.
--
-- Esta migración no da la propiedad a nadie: todos los jobs que reclamaban
-- ese archivo pasan a FAILED (reintentables), sin output_path, con un mensaje
-- que nombra el archivo, a todos los jobs implicados y el estado que se
-- conoce de cada uno. El archivo no se toca. Al reintentar uno, la
-- reclamación previa a la descarga (ADR-0030) lo encuentra y falla hasta que
-- el User lo mueva o lo renombre.
--
-- Los jobs que cambió la 0003 se reconocen por su mensaje, que empieza por
-- "output file "; los fallos de la reclamación en tiempo de ejecución empiezan
-- por la ruta y no coinciden. Su estado anterior a la 0003 no se guardó.

CREATE TEMP TABLE undecided_ownership (
    job_id          INTEGER PRIMARY KEY,
    output_path     TEXT NOT NULL,
    previous_status TEXT
);

INSERT INTO undecided_ownership (job_id, output_path, previous_status)
    SELECT id,
           substr(failure_message, 13, instr(failure_message, ' belongs to job ') - 13),
           NULL
    FROM jobs
    WHERE status = 'FAILED'
      AND output_path IS NULL
      AND failure_reason = 'FILESYSTEM'
      AND failure_message LIKE 'output file % belongs to job %; use an output template that keeps %(id)s';

-- El job al que la 0003 dio el archivo.
INSERT OR IGNORE INTO undecided_ownership (job_id, output_path, previous_status)
    SELECT id, output_path, status
    FROM jobs
    WHERE output_path IN (SELECT output_path FROM undecided_ownership);

UPDATE jobs
SET status = 'FAILED',
    failure_reason = 'FILESYSTEM',
    output_path = NULL,
    failure_message =
        'ownership of output file '
        || (SELECT u.output_path FROM undecided_ownership AS u WHERE u.job_id = jobs.id)
        || ' is ambiguous: jobs '
        || (SELECT group_concat(claimant.job_id, ', ')
            FROM (SELECT other.job_id
                  FROM undecided_ownership AS other
                  WHERE other.output_path = (SELECT u.output_path
                                             FROM undecided_ownership AS u
                                             WHERE u.job_id = jobs.id)
                  ORDER BY other.job_id) AS claimant)
        || ' claimed it; the file was kept and no job owns it; '
        || (SELECT CASE
                       WHEN u.previous_status IS NULL
                           THEN 'its status before migration 0003 was not recorded'
                       ELSE 'this job was ' || u.previous_status
                   END
            FROM undecided_ownership AS u
            WHERE u.job_id = jobs.id)
        || '; move or rename the file, then retry'
WHERE id IN (SELECT job_id FROM undecided_ownership);

DROP TABLE undecided_ownership;
