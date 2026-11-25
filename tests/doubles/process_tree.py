"""Árbol de procesos de prueba: raíz (el papel del worker) → hijo → nieto.

El hijo hace el papel de ffmpeg o deno y se lanza como yt-dlp los lanza, con
subprocess.Popen sin creationflags. El nieto escribe un archivo parcial sin
parar e ignora SIGTERM. Las pruebas siguen cada proceso por handle (OpenProcess
en Windows, pidfd en Linux), nunca por PID, y solo terminan los que crearon.
"""

import contextlib
import multiprocessing
import os
import select
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from multiprocessing.context import SpawnProcess
from multiprocessing.synchronize import Event
from pathlib import Path
from typing import Any

from queued_media_downloader.workers.process_tree_terminator import (
    become_process_tree_root,
)

TREE_ROLES = ("root", "child", "grandchild")
START_TIMEOUT_SECONDS = 30.0
EXIT_TIMEOUT_SECONDS = 10.0
PARTIAL_CHUNK = b"x" * 4096


def tree_root(pid_file: str, part_file: str, registered: Event) -> None:
    """Raíz del árbol: hace lo mismo que el worker real al arrancar.

    Se convierte en raíz de su árbol, espera a que el proceso principal la
    registre y solo entonces lanza procesos, como el worker con su primer job.
    """
    become_process_tree_root()
    _record_pid(pid_file, "root")
    registered.wait()
    subprocess.Popen([sys.executable, __file__, "child", pid_file, part_file])
    _sleep_forever()


def plain_process(pid_file: str) -> None:
    """Proceso que aún no se ha convertido en raíz de su árbol."""
    _record_pid(pid_file, "root")
    _sleep_forever()


def attempt_breakaway(result_file: str, registered: Event) -> None:
    """Intenta crear, ya registrado, un proceso fuera de su árbol (Windows)."""
    registered.wait()
    breakaway_flag = 0x01000000  # CREATE_BREAKAWAY_FROM_JOB
    try:
        escaped = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            creationflags=breakaway_flag,
        )
    except PermissionError:
        Path(result_file).write_text("denied", encoding="utf-8")
        return
    escaped.kill()
    Path(result_file).write_text("escaped", encoding="utf-8")


def _child(pid_file: str, part_file: str) -> None:
    _record_pid(pid_file, "child")
    subprocess.Popen([sys.executable, __file__, "grandchild", pid_file, part_file])
    _sleep_forever()


def _grandchild(pid_file: str, part_file: str) -> None:
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    with Path(part_file).open("ab") as partial:
        partial.write(PARTIAL_CHUNK)
        partial.flush()
        _record_pid(pid_file, "grandchild")
        while True:
            partial.write(PARTIAL_CHUNK)
            partial.flush()
            time.sleep(0.05)


def _record_pid(pid_file: str, role: str) -> None:
    with Path(pid_file).open("a", encoding="utf-8") as pids:
        pids.write(f"{role} {os.getpid()}\n")


def _sleep_forever() -> None:
    while True:
        time.sleep(1)


class WatchedProcess:
    """Proceso seguido por handle: un PID reutilizado no lo confunde."""

    def __init__(self, process_id: int) -> None:
        """Abre el handle; el proceso debe estar vivo."""
        self.process_id = process_id
        self._handle = _open_process(process_id)

    def is_alive(self) -> bool:
        """Indica si sigue en ejecución (un zombi cuenta como terminado)."""
        return _is_alive(self._handle)

    def kill(self) -> None:
        """Lo termina si sigue vivo."""
        if self.is_alive():
            _kill(self._handle)

    def close(self) -> None:
        """Libera el handle."""
        _close(self._handle)


if sys.platform == "win32":
    import ctypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.OpenProcess.restype = ctypes.c_void_p
    _SYNCHRONIZE = 0x00100000
    _PROCESS_TERMINATE = 0x0001
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    def _open_process(process_id: int) -> Any:
        access = _SYNCHRONIZE | _PROCESS_TERMINATE | _PROCESS_QUERY_LIMITED_INFORMATION
        handle = _kernel32.OpenProcess(access, False, process_id)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def _is_alive(handle: Any) -> bool:
        return bool(_kernel32.WaitForSingleObject(ctypes.c_void_p(handle), 0) != 0)

    def _kill(handle: Any) -> None:
        _kernel32.TerminateProcess(ctypes.c_void_p(handle), 1)

    def _close(handle: Any) -> None:
        _kernel32.CloseHandle(ctypes.c_void_p(handle))

else:

    def _open_process(process_id: int) -> Any:
        return os.pidfd_open(process_id)

    def _is_alive(handle: Any) -> bool:
        readable, _, _ = select.select([handle], [], [], 0)
        return not readable

    def _kill(handle: Any) -> None:
        with contextlib.suppress(ProcessLookupError):
            signal.pidfd_send_signal(handle, signal.SIGKILL)

    def _close(handle: Any) -> None:
        os.close(handle)


@dataclass
class ProcessTree:
    """Raíz, hijo y nieto de un árbol de prueba, seguidos por handle."""

    root: SpawnProcess
    processes: dict[str, WatchedProcess]
    part_file: Path

    def alive_roles(self) -> list[str]:
        """Procesos del árbol que siguen vivos."""
        return [role for role, process in self.processes.items() if process.is_alive()]

    def wait_until_dead(self, timeout_seconds: float = EXIT_TIMEOUT_SECONDS) -> None:
        """Espera a que no quede ningún proceso vivo, como mucho timeout_seconds."""
        deadline = time.monotonic() + timeout_seconds
        while self.alive_roles() and time.monotonic() < deadline:
            time.sleep(0.05)

    def clean_up(self) -> None:
        """Termina lo que quede y libera los handles."""
        for process in self.processes.values():
            process.kill()
            process.close()
        self.root.join(EXIT_TIMEOUT_SECONDS)


def start_tree(directory: Path, register: Callable[[int], None]) -> ProcessTree:
    """Arranca un árbol, registra su raíz con register y espera a los tres."""
    context = multiprocessing.get_context("spawn")
    pid_file = directory / "tree.pids"
    part_file = directory / "tree.part"
    registered = context.Event()
    root = context.Process(
        target=tree_root,
        args=(str(pid_file), str(part_file), registered),
        daemon=True,
    )
    root.start()
    assert root.pid is not None
    register(root.pid)
    registered.set()
    process_ids = wait_for_roles(pid_file, TREE_ROLES)
    processes = {role: WatchedProcess(process_ids[role]) for role in TREE_ROLES}
    return ProcessTree(root, processes, part_file)


def wait_until_all_dead(
    processes: list[WatchedProcess], timeout_seconds: float = EXIT_TIMEOUT_SECONDS
) -> bool:
    """Espera a que todos terminen; indica si terminaron a tiempo."""
    deadline = time.monotonic() + timeout_seconds
    while any(process.is_alive() for process in processes):
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)
    return True


def wait_for_roles(pid_file: Path, roles: tuple[str, ...]) -> dict[str, int]:
    """PIDs que anotaron los procesos del árbol, cuando estén todos."""
    deadline = time.monotonic() + START_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        process_ids = read_process_ids(pid_file)
        if all(role in process_ids for role in roles):
            return process_ids
        time.sleep(0.05)
    message = f"Test processes did not start: {read_process_ids(pid_file)}"
    raise TimeoutError(message)


def read_process_ids(pid_file: Path) -> dict[str, int]:
    """Lee las líneas "papel PID" que anotó cada proceso."""
    if not pid_file.exists():
        return {}
    words = pid_file.read_text(encoding="utf-8").split()
    return dict(zip(words[::2], map(int, words[1::2]), strict=True))


if __name__ == "__main__":
    {"child": _child, "grandchild": _grandchild}[sys.argv[1]](sys.argv[2], sys.argv[3])
