"""Contrato con yt-dlp: cómo avisa de que un formato ya no se ofrece.

yt-dlp no tiene una excepción propia para este caso, solo el texto de un
ExtractorError. Si se actualiza la versión fijada, estas pruebas dicen si la
detección de UC-06 A1 sigue valiendo.
"""

import tomllib
from pathlib import Path

import pytest
from yt_dlp import YoutubeDL
from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.utils import DownloadError, ExtractorError
from yt_dlp.version import __version__ as installed_yt_dlp_version

from queued_media_downloader.media_extraction.failure_classifier import (
    FORMAT_UNAVAILABLE_MESSAGE,
    is_format_unavailable,
)

# Versión contra la que se comprobó FORMAT_UNAVAILABLE_MESSAGE: las pruebas de
# abajo lo comprueban con la librería instalada, no solo esta constante.
VERIFIED_YT_DLP_VERSION = "2026.11.23"
PYPROJECT_PATH = Path(__file__).parents[2] / "pyproject.toml"


def pinned_yt_dlp_version() -> str:
    """Versión de yt-dlp que fija pyproject.toml."""
    dependencies = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"][
        "dependencies"
    ]
    [yt_dlp_requirement] = [
        requirement for requirement in dependencies if requirement.startswith("yt-dlp")
    ]
    return str(yt_dlp_requirement).split("==")[1]


def error_for_unavailable_format(media_url: str, tmp_path: Path) -> DownloadError:
    """Error real de yt-dlp al pedir un formato que el contenido no ofrece."""
    parameters = {"format": "999", "paths": {"home": str(tmp_path)}, "quiet": True}
    with YoutubeDL(parameters) as youtube_dl, pytest.raises(DownloadError) as raised:
        youtube_dl.download([media_url])
    return raised.value


def test_message_was_verified_against_the_pinned_and_installed_version() -> None:
    assert pinned_yt_dlp_version() == VERIFIED_YT_DLP_VERSION
    assert installed_yt_dlp_version == VERIFIED_YT_DLP_VERSION


def test_real_unavailable_format_error_is_detected(
    local_media_server: str, tmp_path: Path
) -> None:
    download_error = error_for_unavailable_format(
        f"{local_media_server}/sample.mp4", tmp_path
    )

    assert FORMAT_UNAVAILABLE_MESSAGE in str(download_error)
    assert is_format_unavailable(download_error)


@pytest.mark.parametrize(
    "error",
    [
        ExtractorError("Video unavailable", expected=True),
        DownloadError(
            "ERROR: HTTP Error 404",
            exc_info=(HTTPError, HTTPError.__new__(HTTPError), None),
        ),
        OSError("disk full"),
    ],
    ids=["unavailable media", "http 404", "file system"],
)
def test_other_errors_are_not_an_unavailable_format(error: Exception) -> None:
    assert not is_format_unavailable(error)
