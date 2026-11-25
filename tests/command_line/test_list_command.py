import pytest

from queued_media_downloader.command_line.command_parser import main


@pytest.fixture
def downloaded_playlist(
    local_media_server: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """feed.xml descargado: playlist 1, entradas 2 a 4 y la anidada con su hijo 5."""
    main(["enqueue", f"{local_media_server}/feed.xml"])
    main(["run"])
    capsys.readouterr()


@pytest.mark.usefixtures("downloaded_playlist")
def test_list_shows_one_line_per_job(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert [line.split()[0] for line in lines] == ["1", "2", "3", "4", "5"]
    assert "EXPANSION" in lines[0]
    assert "COMPLETED" in lines[0]


@pytest.mark.usefixtures("downloaded_playlist")
def test_list_filters_by_status_and_by_parent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["list", "--status", "SKIPPED"])
    skipped = capsys.readouterr().out.splitlines()
    main(["list", "--parent", "1"])
    entries = capsys.readouterr().out.splitlines()

    assert [line.split()[0] for line in skipped] == ["5"]
    assert [line.split()[0] for line in entries] == ["2", "3", "4"]


@pytest.mark.usefixtures("downloaded_playlist")
def test_show_of_a_playlist_lists_its_entries_by_status(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["show", "1"]) == 0

    output = capsys.readouterr().out
    assert "Status:          COMPLETED" in output
    assert "Entries:         3 COMPLETED" in output


@pytest.mark.usefixtures("downloaded_playlist")
def test_show_of_an_entry_names_its_playlist(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["show", "2"])

    assert "Playlist:        job 1, 'Local feed', #1" in capsys.readouterr().out


def test_show_of_a_missing_job_is_a_usage_error(
    state_directory: object, capsys: pytest.CaptureFixture[str]
) -> None:
    del state_directory
    assert main(["show", "99"]) == 2
    assert "Job 99 does not exist" in capsys.readouterr().err


def test_list_of_an_empty_queue_says_so(
    state_directory: object, capsys: pytest.CaptureFixture[str]
) -> None:
    del state_directory
    assert main(["list"]) == 0
    assert capsys.readouterr().out == "No jobs\n"
