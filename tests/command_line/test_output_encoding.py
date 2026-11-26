"""Salida de los comandos con una codificación que no tiene todos los caracteres.

En Windows, cuando la salida va a un archivo o a una tubería (por ejemplo,
Tee-Object en la validación), Python escribe en la codificación local, cp1252,
que no tiene emojis: `list` terminaba con UnicodeEncodeError a mitad de la
lista (T42-D4). Aquí se simula con PYTHONIOENCODING=cp1252.
"""

import os
import subprocess
import sys
from pathlib import Path

from queued_media_downloader.job_storage.sqlite_connection import open_database

# Título real de la validación: emojis y una barra de ancho completo (U+FF5C).
TITLE_WITH_EMOJI = "Setup 100% works \U0001f60e\U0001f60e \uff5c guide"


def run_program(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    environment = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    return subprocess.run(
        [sys.executable, "-m", "queued_media_downloader", *arguments],
        capture_output=True,
        env=environment,
        check=False,
        timeout=60,
    )


def test_list_never_fails_on_characters_the_output_encoding_lacks(
    state_directory: Path,
) -> None:
    assert run_program("enqueue", "https://media.example/watch?v=a").returncode == 0
    connection = open_database(state_directory / "queue.sqlite3")
    with connection:
        connection.execute("UPDATE jobs SET title = ?", (TITLE_WITH_EMOJI,))
    connection.close()

    listed = run_program("list")
    shown = run_program("show", "1")

    assert listed.returncode == 0, listed.stderr.decode("utf-8", "replace")
    assert b"Traceback" not in listed.stderr
    assert "Setup 100% works ?? ? guide" in listed.stdout.decode("cp1252")
    assert shown.returncode == 0, shown.stderr.decode("utf-8", "replace")
