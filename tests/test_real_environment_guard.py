import os
from pathlib import Path

from queued_media_downloader.command_line.command_settings import (
    load_command_settings,
)
from tests.real_environment_guard import RealDataSnapshot, real_locations


def write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_a_change_that_keeps_size_and_count_is_still_detected(tmp_path: Path) -> None:
    state = tmp_path / "state"
    write(state / "queue.sqlite3", b"row 1")
    before = RealDataSnapshot.take({"state": state})
    modified_ns = (state / "queue.sqlite3").stat().st_mtime_ns
    write(state / "queue.sqlite3", b"row 2")
    # La misma fecha: solo el contenido cambia, y se nota igual.
    os.utime(state / "queue.sqlite3", ns=(modified_ns, modified_ns))

    differences = before.differences(RealDataSnapshot.take({"state": state}))

    assert differences == ["changed: state/queue.sqlite3"]


def test_created_and_deleted_files_are_reported(tmp_path: Path) -> None:
    downloads = tmp_path / "downloads"
    write(downloads / "old.mp4", b"old")
    before = RealDataSnapshot.take({"downloads": downloads})
    (downloads / "old.mp4").unlink()
    write(downloads / ".partial" / "job-23" / "new.part", b"new")

    differences = before.differences(RealDataSnapshot.take({"downloads": downloads}))

    assert differences == [
        "created: downloads/.partial/job-23/new.part",
        "deleted: downloads/old.mp4",
    ]


def test_an_untouched_location_has_no_differences(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    write(config, b"worker_count = 2\n")
    before = RealDataSnapshot.take({"config": config, "missing": tmp_path / "none"})

    after = RealDataSnapshot.take({"config": config, "missing": tmp_path / "none"})

    assert before.differences(after) == []


def test_every_test_gets_its_own_state_downloads_and_config(tmp_path: Path) -> None:
    write(tmp_path / "config.toml", b"worker_count = 7\n")

    settings = load_command_settings({})

    assert settings.state_directory == tmp_path / "state"
    assert settings.download_directory == tmp_path / "downloads"
    assert settings.worker_count == 7
    assert all(tmp_path not in path.parents for path in real_locations().values())
