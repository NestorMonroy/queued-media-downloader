"""Interpretación de los argumentos de la línea de comandos."""

import argparse
from collections.abc import Sequence
from importlib.metadata import version

from queued_media_downloader.command_line.diagnose_command import add_diagnose_command
from queued_media_downloader.command_line.enqueue_command import add_enqueue_command
from queued_media_downloader.command_line.exit_code import ExitCode
from queued_media_downloader.command_line.run_command import add_run_command

DISTRIBUTION_NAME = "queued-media-downloader"


def build_command_parser() -> argparse.ArgumentParser:
    """Crea el intérprete de argumentos con las opciones y los comandos."""
    command_parser = argparse.ArgumentParser(prog=DISTRIBUTION_NAME)
    command_parser.add_argument(
        "--version",
        action="version",
        version=f"{DISTRIBUTION_NAME} {version(DISTRIBUTION_NAME)}",
    )
    command_parser.set_defaults(program_name=DISTRIBUTION_NAME)
    commands = command_parser.add_subparsers(metavar="COMMAND", required=True)
    add_enqueue_command(commands)
    add_run_command(commands)
    add_diagnose_command(commands)
    return command_parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Interpreta los argumentos y devuelve el código de salida del programa.

    Args:
        arguments: Argumentos sin el nombre del programa; si se omiten, se
            usan los del proceso.

    Returns:
        El código de salida, para que el llamador decida cómo terminar.
    """
    command_parser = build_command_parser()
    try:
        parsed_arguments = command_parser.parse_args(arguments)
    except SystemExit as parser_exit:
        # argparse termina el proceso al mostrar la versión o un error de uso;
        # se convierte en un código de salida para que main sea comprobable.
        return _exit_code_from(parser_exit)
    exit_code: int = parsed_arguments.run_command(parsed_arguments)
    return exit_code


def _exit_code_from(parser_exit: SystemExit) -> int:
    """Traduce la salida de argparse a un código de salida del programa."""
    if parser_exit.code is None or parser_exit.code == 0:
        return ExitCode.SUCCESS
    return ExitCode.USAGE_ERROR
