from pathlib import Path

from queued_media_downloader.media_extraction.partial_files import (
    remove_partial_files_of,
)


def create_files(directory: Path, *names: str) -> None:
    for name in names:
        (directory / name).write_bytes(b"data")


def test_partial_files_of_the_same_media_are_removed(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        "Song [abc].webm",
        "Song [abc].f137.mp4.part",
        "Song [abc].f140.m4a.part",
        "Song [abc].f137.mp4.ytdl",
    )

    removed_paths = remove_partial_files_of(tmp_path / "Song [abc].webm")

    assert sorted(path.name for path in removed_paths) == [
        "Song [abc].f137.mp4.part",
        "Song [abc].f137.mp4.ytdl",
        "Song [abc].f140.m4a.part",
    ]
    assert [path.name for path in tmp_path.iterdir()] == ["Song [abc].webm"]


def test_files_of_other_media_and_finished_files_are_kept(tmp_path: Path) -> None:
    create_files(
        tmp_path,
        "Song [abc].mp4",
        "Song [abc] live [xyz].f18.mp4.part",
        "Other [def].mp4.part",
        "Song [abc].description",
    )

    removed_paths = remove_partial_files_of(tmp_path / "Song [abc].mp4")

    assert removed_paths == []
    assert len(list(tmp_path.iterdir())) == 4
