"""Configuración de un comando: sus opciones más el entorno real y config.toml."""

import os
from collections.abc import Mapping

from queued_media_downloader.configuration import Settings, load_settings, project_root

CONFIG_FILE_NAME = "config.toml"


def load_command_settings(command_line_values: Mapping[str, object]) -> Settings:
    """Carga la configuración con las opciones del comando como mayor prioridad.

    Raises:
        SettingsError: Si algún valor no es válido.
    """
    return load_settings(
        command_line_values, os.environ, project_root() / CONFIG_FILE_NAME
    )
