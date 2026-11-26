"""Experimento de T33: cómo terminar el árbol de procesos de un worker.

Reproduce la jerarquía real del proyecto: un worker arrancado con
multiprocessing (spawn) lanza un hijo con subprocess.Popen, como yt-dlp lanza
ffmpeg o deno, y ese hijo lanza un nieto que escribe un archivo parcial e
ignora SIGTERM. Después prueba cada estrategia de terminación disponible en el
sistema y escribe una tabla con lo observado.

Solo termina procesos que creó el propio experimento. Los sigue por handle
(OpenProcess en Windows, pidfd en Linux) y no por PID, así que la reutilización
de un PID no puede llevarlo a otro proceso. Al terminar, termina lo que quede.

Uso (desde la raíz del repositorio):

    uv run python scripts/experiments/process_tree_termination.py

No es código de producción: no lo importa el paquete ni lo ejecuta pytest.
"""

import argparse
import contextlib
import json
import multiprocessing
import os
import platform
import select
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field
from multiprocessing.synchronize import Event
from pathlib import Path
from typing import Any

PROCESS_ROLES = ("worker", "child", "grandchild")
START_TIMEOUT_SECONDS = 20.0
EXIT_TIMEOUT_SECONDS = 5.0
PARTIAL_CHUNK = b"x" * 4096
IS_WINDOWS = sys.platform == "win32"


# --- Procesos del experimento -------------------------------------------------


def worker_target(pid_file: str, part_file: str, go: Event | None) -> None:
    """Worker de prueba: espera la señal de arranque y lanza el hijo.

    En POSIX crea su propio grupo de procesos, como haría el worker real.
    """
    if sys.platform != "win32":
        os.setpgid(0, 0)
    _record_pid(pid_file, "worker")
    if go is not None:
        go.wait()
    subprocess.Popen([sys.executable, __file__, "child", pid_file, part_file])
    _sleep_forever()


def child_main(pid_file: str, part_file: str) -> None:
    """Hijo (el papel de ffmpeg o deno): lanza el nieto y espera."""
    _record_pid(pid_file, "child")
    subprocess.Popen([sys.executable, __file__, "grandchild", pid_file, part_file])
    _sleep_forever()


def grandchild_main(pid_file: str, part_file: str) -> None:
    """Nieto: ignora SIGTERM y escribe un archivo parcial sin parar."""
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


def abandoned_main(pid_file: str, part_file: str, strategy_name: str) -> None:
    """Proceso principal que crea un árbol y luego muere a la fuerza."""
    strategy = STRATEGIES[strategy_name]()
    tree = start_tree(Path(pid_file), Path(part_file), strategy)
    del tree
    _sleep_forever()


def _record_pid(pid_file: str, role: str) -> None:
    with Path(pid_file).open("a", encoding="utf-8") as pids:
        pids.write(f"{role} {os.getpid()}\n")


def _sleep_forever() -> None:
    while True:
        time.sleep(1)


# --- Seguimiento de procesos por handle ---------------------------------------


class ProcessHandle:
    """Referencia a un proceso que no se confunde con otro de PID reutilizado."""

    def __init__(self, process_id: int) -> None:
        """Abre el handle; el proceso debe estar vivo."""
        self.process_id = process_id
        self._handle = _open_process(process_id)

    def is_alive(self) -> bool:
        """Indica si el proceso sigue en ejecución (un zombi cuenta como muerto)."""
        return _process_is_alive(self._handle)

    def kill(self) -> None:
        """Termina el proceso, si sigue vivo."""
        if self.is_alive():
            _kill_process(self._handle)

    def close(self) -> None:
        """Libera el handle."""
        _close_process(self._handle)


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    SYNCHRONIZE = 0x00100000
    PROCESS_TERMINATE = 0x0001
    PROCESS_SET_QUOTA = 0x0100
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    WAIT_OBJECT_0 = 0
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
    JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9

    class IoCounters(ctypes.Structure):
        """IO_COUNTERS."""

        _fields_ = [
            (name, ctypes.c_ulonglong)
            for name in (
                "ReadOperationCount",
                "WriteOperationCount",
                "OtherOperationCount",
                "ReadTransferCount",
                "WriteTransferCount",
                "OtherTransferCount",
            )
        ]

    class BasicLimitInformation(ctypes.Structure):
        """JOBOBJECT_BASIC_LIMIT_INFORMATION."""

        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimitInformation(ctypes.Structure):
        """JOBOBJECT_EXTENDED_LIMIT_INFORMATION."""

        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    class BasicAccountingInformation(ctypes.Structure):
        """JOBOBJECT_BASIC_ACCOUNTING_INFORMATION."""

        _fields_ = [
            ("TotalUserTime", ctypes.c_int64),
            ("TotalKernelTime", ctypes.c_int64),
            ("ThisPeriodTotalUserTime", ctypes.c_int64),
            ("ThisPeriodTotalKernelTime", ctypes.c_int64),
            ("TotalPageFaultCount", wintypes.DWORD),
            ("TotalProcesses", wintypes.DWORD),
            ("ActiveProcesses", wintypes.DWORD),
            ("TotalTerminatedProcesses", wintypes.DWORD),
        ]

    def _checked(result: Any) -> Any:
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())
        return result

    def _open_process(process_id: int) -> Any:
        access = SYNCHRONIZE | PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION
        return _checked(kernel32.OpenProcess(access, False, process_id))

    def _process_is_alive(handle: Any) -> bool:
        return bool(kernel32.WaitForSingleObject(handle, 0) != WAIT_OBJECT_0)

    def _kill_process(handle: Any) -> None:
        kernel32.TerminateProcess(handle, 1)

    def _close_process(handle: Any) -> None:
        kernel32.CloseHandle(handle)

else:

    def _open_process(process_id: int) -> Any:
        return os.pidfd_open(process_id)

    def _process_is_alive(handle: Any) -> bool:
        readable, _, _ = select.select([handle], [], [], 0)
        return not readable

    def _kill_process(handle: Any) -> None:
        with contextlib.suppress(ProcessLookupError):
            signal.pidfd_send_signal(handle, signal.SIGKILL)

    def _close_process(handle: Any) -> None:
        os.close(handle)


# --- Estrategias de terminación -----------------------------------------------


class Strategy:
    """Una forma de terminar el árbol de un worker."""

    name = ""
    waits_for_registration = True

    def register(self, worker: multiprocessing.process.BaseProcess) -> None:
        """Se llama tras arrancar el worker y antes de que lance procesos."""

    def terminate(self, worker: multiprocessing.process.BaseProcess) -> None:
        """Termina el árbol del worker."""
        raise NotImplementedError

    def details(self) -> dict[str, Any]:
        """Datos que la estrategia puede aportar tras terminar."""
        return {}

    def release(self) -> None:
        """Libera los recursos de la estrategia."""


class WorkerKillOnly(Strategy):
    """Lo que hace hoy ProcessWorkerPool: terminar solo el worker."""

    name = "worker_kill_only"

    def terminate(self, worker: multiprocessing.process.BaseProcess) -> None:
        """multiprocessing.Process.kill: TerminateProcess o SIGKILL al worker."""
        worker.kill()


class ProcessGroup(Strategy):
    """POSIX: el worker crea su grupo y se envía SIGKILL al grupo."""

    name = "process_group"

    def terminate(self, worker: multiprocessing.process.BaseProcess) -> None:
        """SIGKILL al grupo; el worker sin recoger mantiene reservado su PID."""
        assert worker.pid is not None
        if sys.platform != "win32":
            with contextlib.suppress(ProcessLookupError):
                os.killpg(worker.pid, signal.SIGKILL)


if sys.platform == "win32":

    class TaskkillTree(Strategy):
        """Windows: taskkill /T /F, que recorre el árbol por PID padre."""

        name = "taskkill_tree"

        def __init__(self) -> None:
            """Guarda la salida de cada llamada a taskkill."""
            self.outputs: list[str] = []

        def terminate(self, worker: multiprocessing.process.BaseProcess) -> None:
            """Ejecuta taskkill sobre el PID del worker."""
            completed = subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(worker.pid)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.outputs.append(f"{completed.returncode}: {completed.stdout.strip()}")

        def details(self) -> dict[str, Any]:
            """Salida de taskkill."""
            return {"taskkill": self.outputs}

    class JobObject(Strategy):
        """Windows: un Job Object por worker con KILL_ON_JOB_CLOSE."""

        name = "job_object"

        def __init__(self) -> None:
            """Crea el Job Object con KILL_ON_JOB_CLOSE."""
            self._job = _checked(kernel32.CreateJobObjectW(None, None))
            limits = ExtendedLimitInformation()
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            _checked(
                kernel32.SetInformationJobObject(
                    self._job,
                    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                    ctypes.byref(limits),
                    ctypes.sizeof(limits),
                )
            )
            self._released = False

        def register(self, worker: multiprocessing.process.BaseProcess) -> None:
            """Asigna el worker; lo que lance después hereda el Job Object."""
            handle = _checked(
                kernel32.OpenProcess(
                    PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, worker.pid
                )
            )
            try:
                _checked(kernel32.AssignProcessToJobObject(self._job, handle))
            finally:
                kernel32.CloseHandle(handle)

        def terminate(self, worker: multiprocessing.process.BaseProcess) -> None:  # noqa: ARG002
            """TerminateJobObject: termina todos los procesos del Job Object."""
            _checked(kernel32.TerminateJobObject(self._job, 1))

        def details(self) -> dict[str, Any]:
            """Procesos activos y terminados según el propio Job Object."""
            accounting = BasicAccountingInformation()
            _checked(
                kernel32.QueryInformationJobObject(
                    self._job,
                    JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
                    ctypes.byref(accounting),
                    ctypes.sizeof(accounting),
                    None,
                )
            )
            return {
                "job_total_processes": accounting.TotalProcesses,
                "job_active_processes": accounting.ActiveProcesses,
            }

        def release(self) -> None:
            """Cierra el handle del Job Object (con KILL_ON_JOB_CLOSE)."""
            if not self._released:
                _checked(kernel32.CloseHandle(self._job))
                self._released = True

    class JobObjectAssignedLate(JobObject):
        """Job Object asignado cuando el worker ya lanzó su hijo."""

        name = "job_object_assigned_late"
        waits_for_registration = False


STRATEGIES: dict[str, Callable[[], Strategy]] = {"worker_kill_only": WorkerKillOnly}
if sys.platform == "win32":
    STRATEGIES |= {
        "taskkill_tree": TaskkillTree,
        "job_object": JobObject,
        "job_object_assigned_late": JobObjectAssignedLate,
    }
else:
    STRATEGIES["process_group"] = ProcessGroup


# --- Árbol de procesos ----------------------------------------------------------


@dataclass
class ProcessTree:
    """Un worker con su hijo y su nieto, seguidos por handle."""

    worker: multiprocessing.process.BaseProcess | None
    handles: dict[str, ProcessHandle]
    part_file: Path

    def alive_roles(self) -> list[str]:
        """Procesos del árbol que siguen vivos."""
        return [role for role, handle in self.handles.items() if handle.is_alive()]

    def wait_until_dead(self, timeout_seconds: float = EXIT_TIMEOUT_SECONDS) -> None:
        """Espera hasta timeout_seconds a que no quede ningún proceso vivo."""
        deadline = time.monotonic() + timeout_seconds
        while self.alive_roles() and time.monotonic() < deadline:
            time.sleep(0.05)

    def clean_up(self) -> None:
        """Termina lo que quede del árbol, espera a que salga y libera los handles.

        En Windows, TerminateProcess es asíncrono: sin esperar, un nieto aún
        vivo retiene el parcial y la carpeta temporal no se puede borrar
        (T42-D2: la observación se perdía como PermissionError).
        """
        for handle in self.handles.values():
            handle.kill()
        self.wait_until_dead()
        for handle in self.handles.values():
            handle.close()
        if self.worker is not None:
            self.worker.join(EXIT_TIMEOUT_SECONDS)


def start_tree(pid_file: Path, part_file: Path, strategy: Strategy) -> ProcessTree:
    """Arranca un worker de prueba, lo registra y espera a su hijo y su nieto."""
    context = multiprocessing.get_context("spawn")
    go = context.Event() if strategy.waits_for_registration else None
    worker = context.Process(
        target=worker_target, args=(str(pid_file), str(part_file), go), daemon=True
    )
    worker.start()
    if not strategy.waits_for_registration:
        _wait_for_roles(pid_file, PROCESS_ROLES)
    strategy.register(worker)
    if go is not None:
        go.set()
    process_ids = _wait_for_roles(pid_file, PROCESS_ROLES)
    handles = {role: ProcessHandle(process_ids[role]) for role in PROCESS_ROLES}
    return ProcessTree(worker, handles, part_file)


def _wait_for_roles(pid_file: Path, roles: tuple[str, ...]) -> dict[str, int]:
    deadline = time.monotonic() + START_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        process_ids = _read_process_ids(pid_file)
        if all(role in process_ids for role in roles):
            return process_ids
        time.sleep(0.05)
    message = f"Processes did not start in time: {_read_process_ids(pid_file)}"
    raise TimeoutError(message)


def _read_process_ids(pid_file: Path) -> dict[str, int]:
    if not pid_file.exists():
        return {}
    lines = pid_file.read_text(encoding="utf-8").split()
    return dict(zip(lines[::2], map(int, lines[1::2]), strict=True))


# --- Escenarios -------------------------------------------------------------------


@dataclass
class Observation:
    """Lo observado en un escenario con una estrategia."""

    scenario: str
    strategy: str
    alive_after: list[str]
    details: dict[str, Any] = field(default_factory=dict)


@contextlib.contextmanager
def scenario_directory() -> Iterator[Path]:
    """Carpeta temporal para los PIDs y el archivo parcial de un escenario."""
    # Si aun así algo retiene un archivo, la observación ya hecha no se pierde.
    with tempfile.TemporaryDirectory(
        prefix="t33-", ignore_cleanup_errors=True
    ) as directory:
        yield Path(directory)


def terminate_tree(strategy_name: str) -> Observation:
    """El caso básico: terminar el árbol de un worker en plena escritura."""
    strategy = STRATEGIES[strategy_name]()
    with scenario_directory() as directory:
        tree = start_tree(directory / "a.pids", directory / "a.part", strategy)
        try:
            size_before = tree.part_file.stat().st_size
            strategy.terminate(_worker_of(tree))
            tree.wait_until_dead()
            alive = tree.alive_roles()
            details = strategy.details()
            details["partial_bytes_kept"] = tree.part_file.stat().st_size
            details["partial_bytes_before"] = size_before
            details["partial_is_intact"] = _partial_is_intact(tree.part_file)
            strategy.terminate(_worker_of(tree))
            details["repeated_terminate"] = "no error"
        finally:
            tree.clean_up()
            strategy.release()
    return Observation("terminate_tree", strategy_name, alive, details)


def isolation(strategy_name: str) -> Observation:
    """Terminar el árbol de un worker no afecta al de otro."""
    target_strategy = STRATEGIES[strategy_name]()
    other_strategy = STRATEGIES[strategy_name]()
    with scenario_directory() as directory:
        target = start_tree(directory / "a.pids", directory / "a.part", target_strategy)
        other = start_tree(directory / "b.pids", directory / "b.part", other_strategy)
        try:
            target_strategy.terminate(_worker_of(target))
            target.wait_until_dead()
            details = {"target_alive_after": target.alive_roles()}
            alive = other.alive_roles()
        finally:
            for tree in (target, other):
                tree.clean_up()
            target_strategy.release()
            other_strategy.release()
    return Observation("isolation_other_tree_alive", strategy_name, alive, details)


def worker_already_dead(strategy_name: str) -> Observation:
    """El worker murió solo (caída); después se intenta terminar su árbol."""
    strategy = STRATEGIES[strategy_name]()
    with scenario_directory() as directory:
        tree = start_tree(directory / "a.pids", directory / "a.part", strategy)
        try:
            tree.handles["worker"].kill()
            time.sleep(0.5)
            strategy.terminate(_worker_of(tree))
            tree.wait_until_dead()
            alive = tree.alive_roles()
            details = strategy.details()
        finally:
            tree.clean_up()
            strategy.release()
    return Observation("worker_crashed_then_terminate", strategy_name, alive, details)


def main_process_dies(strategy_name: str) -> Observation:
    """El proceso principal muere a la fuerza con un árbol en marcha."""
    with scenario_directory() as directory:
        pid_file = directory / "a.pids"
        abandoned = subprocess.Popen(
            [
                sys.executable,
                __file__,
                "abandoned-main",
                str(pid_file),
                str(directory / "a.part"),
                strategy_name,
            ]
        )
        process_ids = _wait_for_roles(pid_file, PROCESS_ROLES)
        handles = {role: ProcessHandle(process_ids[role]) for role in PROCESS_ROLES}
        tree = ProcessTree(None, handles, directory / "a.part")
        try:
            abandoned.kill()
            abandoned.wait()
            tree.wait_until_dead()
            alive = tree.alive_roles()
        finally:
            tree.clean_up()
    return Observation("main_process_killed", strategy_name, alive)


def _worker_of(tree: ProcessTree) -> multiprocessing.process.BaseProcess:
    assert tree.worker is not None
    return tree.worker


def _partial_is_intact(part_file: Path) -> bool:
    """El parcial solo contiene bloques completos del nieto."""
    content = part_file.read_bytes()
    return set(content) <= {PARTIAL_CHUNK[0]}


SCENARIOS = (terminate_tree, isolation, worker_already_dead, main_process_dies)


def run_all() -> dict[str, Any]:
    """Ejecuta cada escenario con cada estrategia del sistema."""
    observations = []
    for strategy_name in STRATEGIES:
        for scenario in SCENARIOS:
            if strategy_name == "job_object_assigned_late" and scenario is not (
                terminate_tree
            ):
                continue
            try:
                observations.append(scenario(strategy_name))
            except Exception as error:  # Se informa y se sigue con el resto.
                observations.append(
                    Observation(
                        scenario.__name__,
                        strategy_name,
                        ["ERROR"],
                        {"error": repr(error)},
                    )
                )
    return {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "base_executable": getattr(sys, "_base_executable", sys.executable),
        "observations": [asdict(observation) for observation in observations],
    }


def print_table(results: dict[str, Any]) -> None:
    """Escribe los resultados como una tabla Markdown."""
    print(f"Platform: {results['platform']} | Python {results['python']}")
    print("| Scenario | Strategy | Alive after | Details |")
    print("|---|---|---|---|")
    for observation in results["observations"]:
        alive = ", ".join(observation["alive_after"]) or "none"
        details = json.dumps(observation["details"], ensure_ascii=False)
        print(
            f"| {observation['scenario']} | {observation['strategy']} "
            f"| {alive} | {details} |"
        )


def main() -> None:
    """Punto de entrada del experimento y de sus procesos auxiliares."""
    helpers = {"child": child_main, "grandchild": grandchild_main}
    if len(sys.argv) > 1 and sys.argv[1] in helpers:
        helpers[sys.argv[1]](sys.argv[2], sys.argv[3])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "abandoned-main":
        abandoned_main(sys.argv[2], sys.argv[3], sys.argv[4])
        return
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path, help="also write the results as JSON")
    arguments = parser.parse_args()
    results = run_all()
    print_table(results)
    if arguments.json is not None:
        arguments.json.write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
