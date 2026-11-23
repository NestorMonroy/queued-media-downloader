"""Configuración del programa y su orden de prioridad."""

from queued_media_downloader.configuration.settings import Settings
from queued_media_downloader.configuration.settings_loader import (
    SettingsError,
    load_settings,
    project_root,
)

__all__ = ["Settings", "SettingsError", "load_settings", "project_root"]
