import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_migrations import (
    LATEST_SCHEMA_VERSION,
    load_migrations,
)

# Descarga activa mínima, con las columnas obligatorias de la versión 1.
INSERT_DOWNLOAD = """
    INSERT INTO jobs (kind, status, url, extractor_key, media_id,
                      download_options, attempt_count, created_at, updated_at)
    VALUES ('DOWNLOAD', 'PENDING', 'https://media.example/abc', ?, ?, ?, 0,
            '2026-11-23T00:00:00+00:00', '2026-11-23T00:00:00+00:00')
"""


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    database_connection = open_database(tmp_path / "queue.sqlite3")
    yield database_connection
    database_connection.close()


def pragma(connection: sqlite3.Connection, name: str) -> object:
    row = connection.execute(f"PRAGMA {name}").fetchone()
    return row[0]


def test_opening_a_new_database_applies_every_migration(
    connection: sqlite3.Connection,
) -> None:
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    assert pragma(connection, "user_version") == LATEST_SCHEMA_VERSION
    assert {"jobs", "job_requests"} <= tables


def test_reopening_a_database_does_not_reapply_migrations(tmp_path: Path) -> None:
    database_path = tmp_path / "queue.sqlite3"
    open_database(database_path).close()

    reopened_connection = open_database(database_path)
    schema_version = pragma(reopened_connection, "user_version")
    reopened_connection.close()

    assert schema_version == LATEST_SCHEMA_VERSION


@pytest.mark.parametrize(
    ("name", "expected_value"),
    [
        ("journal_mode", "wal"),
        ("foreign_keys", 1),
        ("busy_timeout", 5000),
        ("synchronous", 1),
    ],
    ids=["write-ahead log", "foreign keys", "busy timeout", "synchronous normal"],
)
def test_connection_applies_the_designed_pragmas(
    connection: sqlite3.Connection, name: str, expected_value: object
) -> None:
    assert pragma(connection, name) == expected_value


def test_migration_2_keeps_jobs_and_tells_duplicates_by_output_kind(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "queue.sqlite3"
    version_1 = sqlite3.connect(database_path)
    version_1.executescript(f"{load_migrations()[0].script}\nPRAGMA user_version = 1;")
    version_1.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    version_1.commit()
    version_1.close()

    migrated = open_database(database_path)
    migrated.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": true}'))
    with pytest.raises(sqlite3.IntegrityError):
        migrated.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    job_count = migrated.execute("SELECT count(*) FROM jobs").fetchone()[0]
    schema_version = pragma(migrated, "user_version")
    migrated.close()

    assert schema_version == LATEST_SCHEMA_VERSION
    assert job_count == 2


def database_at_version_2(database_path: Path) -> sqlite3.Connection:
    """Base de datos con las migraciones 1 y 2, como la dejó E1."""
    connection = sqlite3.connect(database_path)
    version_2_scripts = "\n".join(m.script for m in load_migrations()[:2])
    connection.executescript(f"{version_2_scripts}\nPRAGMA user_version = 2;")
    return connection


def test_migration_3_keeps_jobs_their_links_and_their_requests(tmp_path: Path) -> None:
    database_path = tmp_path / "queue.sqlite3"
    version_2 = database_at_version_2(database_path)
    version_2.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    version_2.execute(INSERT_DOWNLOAD, ("Youtube", "def", '{"audio_only": false}'))
    version_2.execute("UPDATE jobs SET parent_id = 1 WHERE id = 2")
    version_2.execute(
        "INSERT INTO job_requests (job_id, request_type, requested_at)"
        " VALUES (2, 'CANCEL', '2026-11-25T00:00:00+00:00')"
    )
    version_2.commit()
    version_2.close()

    migrated = open_database(database_path)
    jobs = migrated.execute("SELECT id, parent_id, media_id FROM jobs").fetchall()
    requests = migrated.execute("SELECT job_id, request_type FROM job_requests")
    foreign_key_problems = migrated.execute("PRAGMA foreign_key_check").fetchall()
    schema_version = pragma(migrated, "user_version")
    request_rows = requests.fetchall()
    migrated.close()

    assert schema_version == LATEST_SCHEMA_VERSION
    assert jobs == [(1, None, "abc"), (2, 1, "def")]
    assert request_rows == [(2, "CANCEL")]
    assert foreign_key_problems == []


def test_job_ids_are_never_reused_after_deleting_the_last_job(tmp_path: Path) -> None:
    # La carpeta de parciales lleva el id del job (T44): un id reutilizado
    # heredaría los parciales de un job borrado.
    database_path = tmp_path / "queue.sqlite3"
    version_2 = database_at_version_2(database_path)
    version_2.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    version_2.execute(INSERT_DOWNLOAD, ("Youtube", "def", '{"audio_only": false}'))
    version_2.commit()
    version_2.close()
    migrated = open_database(database_path)

    migrated.execute("DELETE FROM jobs WHERE id = 2")
    cursor = migrated.execute(
        INSERT_DOWNLOAD, ("Youtube", "ghi", '{"audio_only": false}')
    )
    new_job_id = cursor.lastrowid
    migrated.close()

    assert new_job_id == 3


def test_deleting_a_job_still_deletes_its_children_and_requests(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    connection.execute(INSERT_DOWNLOAD, ("Youtube", "def", '{"audio_only": false}'))
    connection.execute("UPDATE jobs SET parent_id = 1 WHERE id = 2")
    connection.execute(
        "INSERT INTO job_requests (job_id, request_type, requested_at)"
        " VALUES (2, 'CANCEL', '2026-11-25T00:00:00+00:00')"
    )

    connection.execute("DELETE FROM jobs WHERE id = 1")

    assert connection.execute("SELECT count(*) FROM jobs").fetchone()[0] == 0
    assert connection.execute("SELECT count(*) FROM job_requests").fetchone()[0] == 0


def test_two_jobs_cannot_own_the_same_output_file(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    connection.execute(INSERT_DOWNLOAD, ("Youtube", "def", '{"audio_only": false}'))
    connection.execute(
        "UPDATE jobs SET output_path = 'downloads/video.mp4' WHERE id = 1"
    )

    with pytest.raises(sqlite3.IntegrityError, match=r"jobs\.output_path"):
        connection.execute(
            "UPDATE jobs SET output_path = 'downloads/video.mp4' WHERE id = 2"
        )


def test_upgrading_from_version_1_keeps_every_job_and_its_links(tmp_path: Path) -> None:
    database_path = tmp_path / "queue.sqlite3"
    version_1 = sqlite3.connect(database_path)
    version_1.executescript(f"{load_migrations()[0].script}\nPRAGMA user_version = 1;")
    version_1.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    version_1.execute(INSERT_DOWNLOAD, ("Youtube", "def", '{"audio_only": true}'))
    version_1.execute("UPDATE jobs SET parent_id = 1 WHERE id = 2")
    version_1.commit()
    before = version_1.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    version_1.close()

    migrated = open_database(database_path)
    after = migrated.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    indexes = {row[1] for row in migrated.execute("PRAGMA index_list(jobs)").fetchall()}
    foreign_key_problems = migrated.execute("PRAGMA foreign_key_check").fetchall()
    schema_version = pragma(migrated, "user_version")
    migrated.close()

    assert schema_version == LATEST_SCHEMA_VERSION
    assert after == before
    assert foreign_key_problems == []
    assert {
        "jobs_by_status",
        "jobs_by_parent",
        "unique_active_download_per_media",
        "unique_output_path",
    } <= indexes


SHARED_FILE = "/downloads/same.mp4"
OWNERSHIP_COLUMNS = (
    "SELECT id, status, output_path, failure_reason, failure_message"
    " FROM jobs ORDER BY id"
)


def version_2_with_a_file_claimed_three_times(database_path: Path) -> None:
    """Base de E1 (R-14): tres jobs COMPLETED con el mismo archivo final."""
    version_2 = database_at_version_2(database_path)
    for media_id in ("abc", "def", "ghi"):
        version_2.execute(
            INSERT_DOWNLOAD, ("Youtube", media_id, '{"audio_only": false}')
        )
    version_2.execute(
        "UPDATE jobs SET status = 'COMPLETED', output_path = ?", (SHARED_FILE,)
    )
    version_2.commit()
    version_2.close()


def assert_ownership_is_left_undecided(rows: list[tuple[object, ...]]) -> None:
    """Ningún job queda como dueño; el diagnóstico nombra el archivo y a todos."""
    assert [row[:4] for row in rows] == [
        (job_id, "FAILED", None, "FILESYSTEM") for job_id in (1, 2, 3)
    ]
    for row in rows:
        message = str(row[4])
        assert f"ownership of output file {SHARED_FILE} is ambiguous" in message
        assert "jobs 1, 2, 3 claimed it" in message
        assert "the file was kept and no job owns it" in message
    # El estado que la 0003 conservó; el de los demás no se guardó.
    assert "this job was COMPLETED" in str(rows[0][4])
    assert all("was not recorded" in str(row[4]) for row in rows[1:])


def test_a_file_claimed_by_several_version_2_jobs_gets_no_owner(
    tmp_path: Path,
) -> None:
    # El id menor no prueba quién escribió el archivo: con yt-dlp, un job
    # posterior pudo sobrescribirlo (FFmpegExtractAudio) o tomarlo por
    # descargado. Se conserva el archivo y ningún job queda COMPLETED con él.
    database_path = tmp_path / "queue.sqlite3"
    version_2_with_a_file_claimed_three_times(database_path)

    migrated = open_database(database_path)
    rows = migrated.execute(OWNERSHIP_COLUMNS).fetchall()
    unique_paths = migrated.execute(
        "SELECT count(*) FROM jobs WHERE output_path IS NOT NULL"
    ).fetchone()[0]
    migrated.close()

    assert_ownership_is_left_undecided(rows)
    assert unique_paths == 0


def test_migration_4_undoes_the_owner_that_migration_3_chose_by_lowest_id(
    tmp_path: Path,
) -> None:
    # Bases que ya aplicaron la 0003 publicada (2026-11-26), que daba el
    # archivo al id menor.
    database_path = tmp_path / "queue.sqlite3"
    version_2_with_a_file_claimed_three_times(database_path)
    version_3 = sqlite3.connect(database_path)
    version_3.executescript(
        f"BEGIN;\n{load_migrations()[2].script}\nPRAGMA user_version = 3;\nCOMMIT;"
    )
    after_migration_3 = version_3.execute(OWNERSHIP_COLUMNS).fetchall()
    version_3.close()
    assert after_migration_3[0][1:3] == ("COMPLETED", SHARED_FILE)

    migrated = open_database(database_path)
    rows = migrated.execute(OWNERSHIP_COLUMNS).fetchall()
    migrated.close()

    assert_ownership_is_left_undecided(rows)


def test_migration_4_leaves_every_other_job_untouched(tmp_path: Path) -> None:
    database_path = tmp_path / "queue.sqlite3"
    version_3 = sqlite3.connect(database_path)
    scripts = "\n".join(m.script for m in load_migrations()[:3])
    version_3.executescript(f"{scripts}\nPRAGMA user_version = 3;")
    version_3.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    version_3.execute(INSERT_DOWNLOAD, ("Youtube", "def", '{"audio_only": false}'))
    version_3.execute(
        "UPDATE jobs SET status = 'COMPLETED', output_path = '/downloads/a.mp4'"
        " WHERE id = 1"
    )
    # Un fallo de la reclamación en tiempo de ejecución (ADR-0030), no de la
    # migración 0003: su texto no empieza por "output file ".
    version_3.execute(
        "UPDATE jobs SET status = 'FAILED', failure_reason = 'FILESYSTEM',"
        " failure_message = '/downloads/a.* belongs to job 1; the file was left"
        " untouched; use an output template that keeps %(id)s' WHERE id = 2"
    )
    version_3.commit()
    before = version_3.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    version_3.close()

    migrated = open_database(database_path)
    after = migrated.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    migrated.close()

    assert after == before


class ClosingSpy:
    """Envuelve una conexión real para saber si open_database la cerró."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.closed = False

    def __getattr__(self, name: str) -> object:
        return getattr(self.connection, name)

    def close(self) -> None:
        self.closed = True
        self.connection.close()


def test_a_failing_migration_leaves_the_database_as_it_was_and_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from queued_media_downloader.job_storage import sqlite_migrations

    database_path = tmp_path / "queue.sqlite3"
    version_2 = database_at_version_2(database_path)
    version_2.execute(INSERT_DOWNLOAD, ("Youtube", "abc", '{"audio_only": false}'))
    version_2.commit()
    before = version_2.execute("SELECT * FROM jobs").fetchall()
    version_2.close()
    failing = sqlite_migrations.Migration(
        number=3, script="CREATE TABLE half_done (x);\nSELECT * FROM missing_table;"
    )
    real_migrations = sqlite_migrations.load_migrations()[:2]
    monkeypatch.setattr(
        sqlite_migrations, "load_migrations", lambda: [*real_migrations, failing]
    )
    spies: list[ClosingSpy] = []
    real_connect = sqlite3.connect

    def connect_with_spy(path: Path) -> ClosingSpy:
        spy = ClosingSpy(real_connect(path))
        spies.append(spy)
        return spy

    monkeypatch.setattr(sqlite3, "connect", connect_with_spy)

    with pytest.raises(sqlite3.OperationalError, match="missing_table"):
        open_database(database_path)

    monkeypatch.undo()
    check = sqlite3.connect(database_path)
    tables = {row[0] for row in check.execute("SELECT name FROM sqlite_master")}
    after = check.execute("SELECT * FROM jobs").fetchall()
    version = check.execute("PRAGMA user_version").fetchone()[0]
    check.close()
    assert spies[0].closed
    assert version == 2
    assert "half_done" not in tables
    assert after == before
