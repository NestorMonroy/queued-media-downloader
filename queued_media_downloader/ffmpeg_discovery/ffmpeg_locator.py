"""Contrato de localización de ffmpeg y lo que devuelve (ADR-0006)."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class FfmpegSource(StrEnum):
    """De dónde salió el ffmpeg que se usa, en el orden en que se busca."""

    CONFIGURED = "CONFIGURED"
    VENDORED = "VENDORED"
    SYSTEM_PATH = "SYSTEM_PATH"


@dataclass(frozen=True, slots=True, kw_only=True)
class FfmpegInstallation:
    """ffmpeg y ffprobe listos para usarse.

    ffmpeg_location es lo que recibe yt-dlp en el parámetro del mismo nombre;
    None significa que yt-dlp los busque en el PATH.
    """

    source: FfmpegSource
    ffmpeg_location: Path | None
    ffmpeg_version: str
    ffprobe_version: str

    @property
    def is_validated(self) -> bool:
        """Solo la build incluida es una versión probada con el proyecto."""
        return self.source is FfmpegSource.VENDORED


class FfmpegUnavailableError(Exception):
    """No hay un ffmpeg utilizable; el mensaje dice cómo corregirlo."""


class FfmpegLocator(Protocol):
    """Encuentra y verifica ffmpeg y ffprobe."""

    def locate(self) -> FfmpegInstallation:
        """Devuelve la instalación que se debe usar.

        Raises:
            FfmpegUnavailableError: Si no hay un ffmpeg utilizable.
        """
        ...
