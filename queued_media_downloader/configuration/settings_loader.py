"""Carga de la configuración con su orden de prioridad (SUP-F03).

Prioridad, de mayor a menor: línea de comandos, variables de entorno
QUEUED_MEDIA_DOWNLOADER_*, archivo config.toml y valores por defecto.
"""

import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from queued_media_downloader.configuration.settings import Settings

ENVIRONMENT_PREFIX = "QUEUED_MEDIA_DOWNLOADER_"


class SettingsError(Exception):
    """Un valor de configuración falta, sobra o no es válido."""


def project_root() -> Path:
    """Carpeta del proyecto: la que contiene el paquete queued_media_downloader.

    El proyecto se usa desde su clon con uv, que lo instala en modo editable,
    así que el paquete siempre está dentro de la carpeta del proyecto.
    """
    return Path(__file__).resolve().parents[2]


def _positive_integer(value: object) -> int:
    """Convierte a entero mayor que cero."""
    if isinstance(value, bool) or not isinstance(value, int | str):
        raise ValueError("must be a positive integer")
    number = int(value)
    if number <= 0:
        raise ValueError("must be a positive integer")
    return number


def _positive_number(value: object) -> float:
    """Convierte a número mayor que cero."""
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise ValueError("must be a positive number")
    number = float(value)
    if number <= 0:
        raise ValueError("must be a positive number")
    return number


def _non_empty_text(value: object) -> str:
    """Exige un texto con contenido."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("must be a non-empty text")
    return value


def _path(value: object) -> Path:
    """Convierte a ruta, expandiendo ~ al directorio del usuario."""
    return Path(_non_empty_text(str(value))).expanduser()


@dataclass(frozen=True, slots=True)
class SettingDefinition:
    """Valor por defecto y conversión de una clave de configuración."""

    default: Callable[[], object]
    convert: Callable[[object], object]


SETTING_DEFINITIONS: Mapping[str, SettingDefinition] = {
    "download_directory": SettingDefinition(
        lambda: Path.home() / "Downloads" / "queued-media-downloader", _path
    ),
    "state_directory": SettingDefinition(lambda: project_root() / "state", _path),
    "worker_count": SettingDefinition(lambda: 1, _positive_integer),
    "progress_interval_seconds": SettingDefinition(lambda: 0.5, _positive_number),
    # Espera antes de terminar un worker que no confirma la cancelación (UC-05 A2).
    "cancellation_grace_seconds": SettingDefinition(lambda: 10.0, _positive_number),
    "default_format_selector": SettingDefinition(lambda: "bv*+ba/b", _non_empty_text),
    "single_media_output_template": SettingDefinition(
        lambda: "%(title)s [%(id)s].%(ext)s", _non_empty_text
    ),
    "max_filename_length": SettingDefinition(lambda: 150, _positive_integer),
    "ffmpeg_path": SettingDefinition(lambda: None, _path),
}


def load_settings(
    command_line_values: Mapping[str, object],
    environment: Mapping[str, str],
    config_file: Path,
) -> Settings:
    """Combina las cuatro fuentes y valida cada valor.

    Args:
        command_line_values: Valores de la línea de comandos por clave; None
            significa que la opción no se indicó.
        environment: Variables de entorno del proceso.
        config_file: Ruta de config.toml; si no existe, se ignora.

    Raises:
        SettingsError: Si una clave es desconocida, un valor no es válido o el
            archivo no se puede interpretar.
    """
    values = {
        name: definition.default() for name, definition in SETTING_DEFINITIONS.items()
    }
    sources = (
        (_read_config_file(config_file), str(config_file)),
        (_read_environment(environment), "the environment"),
        (_read_command_line(command_line_values), "the command line"),
    )
    for source_values, source_name in sources:
        for name, raw_value in source_values.items():
            values[name] = _convert(name, raw_value, source_name)
    # Cada conversión de SETTING_DEFINITIONS devuelve el tipo de su campo, algo
    # que mypy no puede deducir de un diccionario de valores heterogéneos.
    return Settings(**values)  # type: ignore[arg-type]


def _read_config_file(config_file: Path) -> dict[str, object]:
    """Lee config.toml; un archivo inexistente equivale a no configurar nada."""
    if not config_file.is_file():
        return {}
    try:
        file_values = tomllib.loads(config_file.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as decode_error:
        message = f"Cannot read {config_file}: {decode_error}"
        raise SettingsError(message) from decode_error
    _reject_unknown_names(file_values, f"setting in {config_file}")
    return file_values


def _read_environment(environment: Mapping[str, str]) -> dict[str, object]:
    """Extrae las variables con el prefijo del programa, por clave."""
    environment_values: dict[str, object] = {}
    for variable, raw_value in environment.items():
        if variable.startswith(ENVIRONMENT_PREFIX):
            name = variable.removeprefix(ENVIRONMENT_PREFIX).lower()
            if name not in SETTING_DEFINITIONS:
                message = f"Unknown environment variable {variable}"
                raise SettingsError(message)
            environment_values[name] = raw_value
    return environment_values


def _read_command_line(command_line_values: Mapping[str, object]) -> dict[str, object]:
    """Descarta las opciones no indicadas (None)."""
    given_values = {
        name: value for name, value in command_line_values.items() if value is not None
    }
    _reject_unknown_names(given_values, "command line setting")
    return given_values


def _reject_unknown_names(
    source_values: Mapping[str, object], description: str
) -> None:
    """Lanza SettingsError si alguna clave no es una clave de configuración."""
    for name in source_values:
        if name not in SETTING_DEFINITIONS:
            message = f"Unknown {description}: {name}"
            raise SettingsError(message)


def _convert(name: str, raw_value: object, source_name: str) -> object:
    """Convierte y valida un valor; el error nombra la clave y su origen."""
    try:
        return SETTING_DEFINITIONS[name].convert(raw_value)
    except ValueError as conversion_error:
        message = f"Invalid value for {name} in {source_name}: {conversion_error}"
        raise SettingsError(message) from conversion_error
