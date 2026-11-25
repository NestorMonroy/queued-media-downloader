import logging
from pathlib import Path

import pytest

from queued_media_downloader.media_extraction.partial_files import (
    remove_partial_files_of,
)


def create_files(directory: Path, *names: str) -> None:
    for name in names:
        (directory / name).write_bytes(b"data")


def remaining_names(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.iterdir())


def test_parts_of_a_previous_merged_format_are_removed(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        "Song [abc].webm",
        "Song [abc].f137.mp4.part",
        "Song [abc].f137.mp4.ytdl",
        "Song [abc].f140.m4a.part",
    )

    removed_paths = remove_partial_files_of(tmp_path / "Song [abc].webm", "137+140")

    assert [path.name for path in removed_paths] == [
        "Song [abc].f137.mp4.part",
        "Song [abc].f137.mp4.ytdl",
        "Song [abc].f140.m4a.part",
    ]
    assert remaining_names(tmp_path) == ["Song [abc].webm"]


def test_partial_file_of_a_previous_single_format_is_removed(tmp_path: Path) -> None:
    create_files(tmp_path, "Song [abc].webm", "Song [abc].mp4.part")

    remove_partial_files_of(tmp_path / "Song [abc].webm", "18")

    assert remaining_names(tmp_path) == ["Song [abc].webm"]


def test_parts_of_other_formats_with_the_same_name_are_kept(tmp_path: Path) -> None:
    # El mismo nombre base no prueba que sea el mismo job: un título largo
    # recortado por max_filename_length pierde el [id] (análisis de T32).
    create_files(
        tmp_path,
        "Song [abc].webm",
        "Song [abc].f251.webm.part",
        "Song [abc].f1370.mp4.part",
    )

    removed_paths = remove_partial_files_of(tmp_path / "Song [abc].webm", "137+140")

    assert removed_paths == []
    assert len(remaining_names(tmp_path)) == 3


def test_files_of_other_media_and_finished_files_are_kept(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        "Song [abc].mp4",
        "Song [abc] live [xyz].mp4.part",
        "Other [def].mp4.part",
        "Song [abc].description",
        "Song [abc].en.vtt",
    )

    removed_paths = remove_partial_files_of(tmp_path / "Song [abc].mp4", "18")

    assert removed_paths == []
    assert len(remaining_names(tmp_path)) == 5


def test_format_id_is_matched_literally(tmp_path: Path) -> None:
    create_files(tmp_path, "S.webm", "S.fdash-v=1.mp4.part", "S.fdashXv=1.mp4.part")

    remove_partial_files_of(tmp_path / "S.webm", "dash-v=1+251")

    assert remaining_names(tmp_path) == ["S.fdashXv=1.mp4.part", "S.webm"]


def test_repeating_the_cleanup_removes_nothing_more(tmp_path: Path) -> None:
    create_files(tmp_path, "Song [abc].webm", "Song [abc].f137.mp4.part")
    remove_partial_files_of(tmp_path / "Song [abc].webm", "137+140")

    assert remove_partial_files_of(tmp_path / "Song [abc].webm", "137+140") == []


def test_file_that_cannot_be_removed_is_kept_without_failing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # En Windows, un .part que otro proceso tiene abierto no se puede borrar.
    create_files(tmp_path, "Song [abc].webm", "Song [abc].mp4.part")
    locked_path = tmp_path / "Song [abc].mp4.part"
    unlink_attempts: list[Path] = []

    def unlink_locked(path: Path, missing_ok: bool = False) -> None:  # noqa: ARG001
        unlink_attempts.append(path)
        raise PermissionError(13, "The file is being used by another process", path)

    monkeypatch.setattr(Path, "unlink", unlink_locked)

    with caplog.at_level(logging.WARNING):
        removed_paths = remove_partial_files_of(tmp_path / "Song [abc].webm", "18")

    assert unlink_attempts == [locked_path]
    assert removed_paths == []
    assert locked_path.exists()
    assert "being used by another process" in caplog.text


def test_file_removed_by_someone_else_meanwhile_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_files(tmp_path, "Song [abc].webm", "Song [abc].mp4.part")
    unlink_attempts: list[Path] = []

    def unlink_vanished(path: Path, missing_ok: bool = False) -> None:  # noqa: ARG001
        unlink_attempts.append(path)
        raise FileNotFoundError(2, "No such file", path)

    monkeypatch.setattr(Path, "unlink", unlink_vanished)

    assert remove_partial_files_of(tmp_path / "Song [abc].webm", "18") == []
    assert unlink_attempts == [tmp_path / "Song [abc].mp4.part"]
