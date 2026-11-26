"""run con la base de datos ocupada por otro proceso más allá de busy_timeout.

En la validación en Windows, otro proceso retuvo un bloqueo de escritura
mientras run descargaba: run terminó con "the queue is busy … nothing was
changed" y dejó el job RUNNING (T42-D12). run es el proceso largo de la cola:
espera a que la cola quede libre, en lugar de abandonar los jobs en curso.
"""

import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from queued_media_downloader.command_line import main
from queued_media_downloader.jobs import Job, JobStatus

# Más que busy_timeout (5 s): sin esperar, la primera escritura de run falla.
LOCK_SECONDS = 6.5


@contextmanager
def write_lock_held_by_another_program(database_path: Path) -> Iterator[None]:
    """Retiene un bloqueo de escritura durante LOCK_SECONDS en otro hilo."""
    locked = threading.Event()

    def hold_lock() -> None:
        connection = sqlite3.connect(database_path, isolation_level=None)
        connection.execute("BEGIN IMMEDIATE")
        locked.set()
        threading.Event().wait(LOCK_SECONDS)
        connection.execute("ROLLBACK")
        connection.close()

    holder = threading.Thread(target=hold_lock)
    holder.start()
    locked.wait()
    try:
        yield
    finally:
        holder.join()


def test_run_waits_for_a_busy_queue_and_completes_the_job(
    local_media_server: str,
    state_directory: Path,
    read_stored_job: Callable[[int], Job],
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["enqueue", f"{local_media_server}/sample.mp4"])

    with write_lock_held_by_another_program(state_directory / "queue.sqlite3"):
        exit_code = main(["run"])

    output = capsys.readouterr()
    assert exit_code == 0, output.err
    assert "The queue is busy; waiting until another program releases it" in (
        output.out
    )
    assert read_stored_job(1).status is JobStatus.COMPLETED
