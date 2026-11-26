"""Una base de datos que no se puede abrir o migrar (auditoría §9)."""

import sqlite3
from pathlib import Path

import pytest

from queued_media_downloader.command_line.command_parser import main
from queued_media_downloader.job_storage import sqlite_migrations


def test_a_failing_migration_is_reported_and_leaves_the_queue_as_it_was(
    state_directory: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main(["enqueue", "https://media.example/watch?v=a"])
    database_path = state_directory / "queue.sqlite3"
    before = sqlite3.connect(database_path).execute("SELECT * FROM jobs").fetchall()
    broken = sqlite_migrations.Migration(
        number=sqlite_migrations.LATEST_SCHEMA_VERSION + 1,
        script="CREATE TABLE half_done (x);\nSELECT * FROM missing_table;",
    )
    real_migrations = sqlite_migrations.load_migrations()
    monkeypatch.setattr(
        sqlite_migrations, "load_migrations", lambda: [*real_migrations, broken]
    )
    capsys.readouterr()

    exit_code = main(["list"])

    check = sqlite3.connect(database_path)
    after = check.execute("SELECT * FROM jobs").fetchall()
    version = check.execute("PRAGMA user_version").fetchone()[0]
    tables = {row[0] for row in check.execute("SELECT name FROM sqlite_master")}
    check.close()
    error = capsys.readouterr().err
    assert exit_code == 1
    assert "cannot open the queue database" in error
    assert "missing_table" in error
    assert "Traceback" not in error
    assert after == before
    assert version == sqlite_migrations.LATEST_SCHEMA_VERSION
    assert "half_done" not in tables


def test_a_file_that_is_not_a_database_is_reported(
    state_directory: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state_directory.mkdir(parents=True)
    (state_directory / "queue.sqlite3").write_bytes(b"not a database" * 100)

    exit_code = main(["list"])

    assert exit_code == 1
    assert "cannot open the queue database" in capsys.readouterr().err
    assert (state_directory / "queue.sqlite3").read_bytes() == b"not a database" * 100
