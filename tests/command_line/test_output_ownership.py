"""Ningún job sobrescribe, borra ni modifica el archivo final de otro (R-14, §7).

Con la plantilla "same.%(ext)s" dos contenidos distintos reciben el mismo
nombre. Sin la reclamación previa, yt-dlp tomaría el archivo del primero por
"ya descargado" y le aplicaría fixup (FixupM4a rehace un .m4a de DASH).
"""

import hashlib
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from queued_media_downloader.command_line import main
from queued_media_downloader.jobs import FailureReason, Job, JobStatus
from tests.command_line.conftest import (
    ENVIRONMENT_PREFIX,
    MP4_CODEC_ARGUMENTS,
    program_for_tests,
    write_dash_media,
)

SHARED_TEMPLATE = "same.%(ext)s"


def fingerprint(path: Path) -> tuple[int, int, str]:
    """Tamaño, fecha de modificación en ns y SHA-256: cualquier cambio se nota."""
    status = path.stat()
    return (
        status.st_size,
        status.st_mtime_ns,
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )


@pytest.fixture
def two_dash_media(local_media_server: str, tmp_path: Path) -> tuple[str, str]:
    """Dos contenidos DASH distintos, con audio en MP4.

    Los ids (first, second) y las duraciones (2 s y 3 s) son distintos: la
    duración dice de qué contenido es un archivo.
    """
    urls = []
    for name, duration_seconds in (("first", 2), ("second", 3)):
        directory = tmp_path / "served" / name
        write_dash_media(directory, MP4_CODEC_ARGUMENTS, duration_seconds)
        # El extractor genérico toma el id del nombre del manifiesto.
        (directory / "sample.mpd").rename(directory / f"{name}.mpd")
        urls.append(f"{local_media_server}/{name}/{name}.mpd")
    return urls[0], urls[1]


@pytest.fixture
def shared_template(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        f"{ENVIRONMENT_PREFIX}SINGLE_MEDIA_OUTPUT_TEMPLATE", SHARED_TEMPLATE
    )


def duration_seconds(media_path: Path) -> int:
    """Duración del archivo, redondeada, según ffprobe."""
    completed_process = subprocess.run(
        [
            str(program_for_tests("ffprobe")),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return round(float(completed_process.stdout))


def claim_files(state_directory: Path) -> list[Path]:
    return sorted((state_directory / "output-claims").glob("*.claim"))


@pytest.mark.usefixtures("shared_template")
def test_a_job_never_modifies_the_finished_audio_file_of_another_job(
    two_dash_media: tuple[str, str],
    tmp_path: Path,
    read_stored_job: Callable[[int], Job],
    stream_types: Callable[[Path], list[str]],
) -> None:
    first_url, second_url = two_dash_media
    main(["enqueue", first_url, "--audio-only"])
    main(["run"])
    audio_path = tmp_path / "downloads" / "audio" / "same.m4a"
    before = fingerprint(audio_path)
    main(["enqueue", second_url, "--audio-only"])

    exit_code = main(["run"])

    second = read_stored_job(2)
    assert exit_code == 1
    assert read_stored_job(1).output_path == str(audio_path)
    assert second.status is JobStatus.FAILED
    assert second.failure_reason is FailureReason.FILESYSTEM
    assert "belongs to job 1" in str(second.failure_message)
    assert second.output_path is None
    assert fingerprint(audio_path) == before
    assert stream_types(audio_path) == ["audio"]
    assert sorted(p.name for p in audio_path.parent.iterdir()) == ["same.m4a"]


@pytest.mark.usefixtures("shared_template")
def test_a_file_the_queue_did_not_write_is_never_taken_or_modified(
    two_dash_media: tuple[str, str],
    tmp_path: Path,
    state_directory: Path,
    read_stored_job: Callable[[int], Job],
) -> None:
    # Un archivo del usuario, de una versión anterior o de un job purgado.
    user_file = tmp_path / "downloads" / "audio" / "same.m4a"
    user_file.parent.mkdir(parents=True)
    user_file.write_bytes(b"not a media file, and not the queue's")
    before = fingerprint(user_file)
    main(["enqueue", two_dash_media[0], "--audio-only"])

    exit_code = main(["run"])

    job = read_stored_job(1)
    assert exit_code == 1
    assert job.failure_reason is FailureReason.FILESYSTEM
    assert "already exists" in str(job.failure_message)
    assert fingerprint(user_file) == before
    assert claim_files(state_directory) == []


@pytest.mark.usefixtures("shared_template")
def test_two_jobs_racing_for_one_name_leave_one_intact_file(
    two_dash_media: tuple[str, str],
    tmp_path: Path,
    read_stored_job: Callable[[int], Job],
    stream_types: Callable[[Path], list[str]],
) -> None:
    main(["enqueue", *two_dash_media])

    exit_code = main(["run", "--worker-count", "2"])

    jobs = [read_stored_job(1), read_stored_job(2)]
    [completed] = [job for job in jobs if job.status is JobStatus.COMPLETED]
    [failed] = [job for job in jobs if job.status is JobStatus.FAILED]
    assert exit_code == 1
    assert failed.failure_reason is FailureReason.FILESYSTEM
    output_path = tmp_path / "downloads" / "same.mp4"
    assert completed.output_path == str(output_path)
    assert stream_types(output_path) == ["audio", "video"]
    # El archivo es el contenido del job que lo completó, no el del otro.
    assert duration_seconds(output_path) == {1: 2, 2: 3}[int(completed.job_id or 0)]
    assert sorted(p.name for p in (tmp_path / "downloads").iterdir()) == [
        ".partial",
        "same.mp4",
    ]


@pytest.mark.usefixtures("shared_template")
def test_purge_releases_the_name_but_the_file_still_protects_itself(
    two_dash_media: tuple[str, str],
    tmp_path: Path,
    state_directory: Path,
    read_stored_job: Callable[[int], Job],
) -> None:
    main(["enqueue", two_dash_media[0]])
    main(["run"])
    video_path = tmp_path / "downloads" / "same.mp4"
    before = fingerprint(video_path)
    assert len(claim_files(state_directory)) == 1

    main(["purge"])
    main(["enqueue", two_dash_media[1]])
    exit_code = main(["run"])

    assert claim_files(state_directory) == []
    assert exit_code == 1
    assert "already exists" in str(read_stored_job(2).failure_message)
    assert fingerprint(video_path) == before
