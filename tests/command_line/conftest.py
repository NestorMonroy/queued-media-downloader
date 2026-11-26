"""Fixtures de las pruebas de los comandos."""

import os
import shutil
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from queued_media_downloader.configuration import project_root
from queued_media_downloader.ffmpeg_discovery.file_system_ffmpeg_locator import (
    VENDORED_BUILD_NAME,
)
from queued_media_downloader.job_storage.sqlite_connection import open_database
from queued_media_downloader.job_storage.sqlite_job_store import SqliteJobStore
from queued_media_downloader.jobs import Job, JobId

ENVIRONMENT_PREFIX = "QUEUED_MEDIA_DOWNLOADER_"


@pytest.fixture
def state_directory(isolated_environment: Path) -> Path:
    """Carpeta de estado propia de la prueba.

    El aislamiento lo da isolated_environment (tests/conftest.py), autouse
    para todas las pruebas: una prueba que olvide pedirlo no puede escribir
    en la cola real del usuario (pasó en T45 y T46).
    """
    return isolated_environment


@pytest.fixture
def read_stored_job(state_directory: Path) -> Iterator[Callable[[int], Job]]:
    """Función que lee un job de la base de datos que dejaron los comandos."""
    opened_connections = []

    def read(job_id: int) -> Job:
        connection = open_database(state_directory / "queue.sqlite3")
        opened_connections.append(connection)
        return SqliteJobStore(connection).get(JobId(job_id))

    yield read
    for connection in opened_connections:
        connection.close()


def program_for_tests(program: str) -> Path:
    """ffmpeg o ffprobe de las pruebas; omite la prueba si no hay ninguno.

    En Windows se usa la build incluida; en otro sistema, la del PATH
    (UC-03, escenarios de prueba).
    """
    if os.name == "nt":
        bin_directory = (
            project_root() / "vendor" / "ffmpeg" / VENDORED_BUILD_NAME / "bin"
        )
        return bin_directory / f"{program}.exe"
    program_path = shutil.which(program)
    if program_path is None:
        pytest.skip(f"{program} is not on PATH")
    return Path(program_path)


# Video y audio en MP4 (.mp4 y .m4a), y en WebM (VP9 y Opus), como sirve YouTube
# la mayoría de sus videos: ahí el audio y el video unido comparten extensión.
MP4_CODEC_ARGUMENTS = ("-c:v", "mpeg4", "-c:a", "aac")
WEBM_CODEC_ARGUMENTS = (
    "-c:v",
    "libvpx-vp9",
    "-deadline",
    "realtime",
    "-cpu-used",
    "8",
    "-c:a",
    "libopus",
)


def write_dash_media(
    directory: Path, codec_arguments: tuple[str, ...], duration_seconds: int = 2
) -> None:
    """Genera con ffmpeg un manifiesto DASH con video y audio separados."""
    directory.mkdir()
    subprocess.run(
        [
            str(program_for_tests("ffmpeg")),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=duration={duration_seconds}:size=160x120:rate=10",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration_seconds}",
            "-map",
            "0:v",
            "-map",
            "1:a",
            *codec_arguments,
            "-f",
            "dash",
            "-seg_duration",
            "1",
            "sample.mpd",
        ],
        cwd=directory,
        check=True,
        timeout=60,
    )


@pytest.fixture
def dash_manifest_url(local_media_server: str, tmp_path: Path) -> str:
    """URL de un manifiesto DASH en MP4 con video y audio separados.

    yt-dlp elige bv*+ba y necesita ffmpeg para unirlos. Los medios se generan
    con ffmpeg en la carpeta que sirve local_media_server.
    """
    write_dash_media(tmp_path / "served" / "dash", MP4_CODEC_ARGUMENTS)
    return f"{local_media_server}/dash/sample.mpd"


@pytest.fixture
def webm_dash_manifest_url(local_media_server: str, tmp_path: Path) -> str:
    """URL de un manifiesto DASH en WebM: el video unido y el audio son .webm."""
    write_dash_media(tmp_path / "served" / "dash-webm", WEBM_CODEC_ARGUMENTS)
    return f"{local_media_server}/dash-webm/sample.mpd"


@pytest.fixture
def stream_types() -> Callable[[Path], list[str]]:
    """Función que devuelve los tipos de stream de un archivo, según ffprobe."""
    ffprobe = program_for_tests("ffprobe")

    def read(media_path: Path) -> list[str]:
        completed_process = subprocess.run(
            [
                str(ffprobe),
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                str(media_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        return sorted(completed_process.stdout.split())

    return read
