"""Comando diagnose: comprueba que el entorno está listo (UC-01)."""

import argparse
import sys

from queued_media_downloader.command_line.command_settings import (
    load_command_settings,
)
from queued_media_downloader.command_line.composition_root import (
    create_diagnose_environment,
)
from queued_media_downloader.command_line.exit_code import ExitCode
from queued_media_downloader.configuration import SettingsError
from queued_media_downloader.diagnostics import CheckOutcome

# Marca de cada resultado; del mismo ancho para que las líneas queden alineadas.
OUTCOME_MARKS = {
    CheckOutcome.PASSED: "[ OK ]",
    CheckOutcome.WARNING: "[WARN]",
    CheckOutcome.FAILED: "[FAIL]",
}


def add_diagnose_command(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Registra el comando diagnose (diseño, Parte 2, §4.1)."""
    diagnose_parser = commands.add_parser(
        "diagnose", help="check ffmpeg, ffprobe, deno and the database"
    )
    diagnose_parser.set_defaults(run_command=run_diagnose_command)


def run_diagnose_command(arguments: argparse.Namespace) -> int:
    """Muestra una línea por componente y un resumen.

    Returns:
        SUCCESS si ninguna comprobación falló (los avisos no cuentan) y
        USAGE_ERROR si falló alguna o la configuración no es válida
        (UC-01, A1, A5 y A6).
    """
    try:
        settings = load_command_settings({})
    except SettingsError as settings_error:
        print(f"{arguments.program_name}: error: {settings_error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR
    checks = create_diagnose_environment(settings).execute()
    for check in checks:
        print(f"{OUTCOME_MARKS[check.outcome]} {check.component}: {check.detail}")
    failed_count = sum(check.outcome is CheckOutcome.FAILED for check in checks)
    if failed_count == 0:
        print("Environment ready")
        return ExitCode.SUCCESS
    noun = "check" if failed_count == 1 else "checks"
    print(f"{failed_count} {noun} failed")
    return ExitCode.USAGE_ERROR
