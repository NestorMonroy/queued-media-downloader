"""Dónde está ffmpeg y si es válido."""

from queued_media_downloader.ffmpeg_discovery.ffmpeg_locator import (
    FfmpegInstallation,
    FfmpegLocator,
    FfmpegSource,
    FfmpegUnavailableError,
)

__all__ = [
    "FfmpegInstallation",
    "FfmpegLocator",
    "FfmpegSource",
    "FfmpegUnavailableError",
]
