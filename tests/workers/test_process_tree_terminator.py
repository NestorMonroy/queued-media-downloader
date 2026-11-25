"""Contrato ProcessTreeTerminator (ADR-0013, ADR-0029) con procesos reales.

Las mismas comprobaciones se ejecutan con la implementación de la plataforma:
grupos de procesos en POSIX, aquí; Job Object en Windows, marcadas `windows`
(campaña final). Lo que solo Windows garantiza (el árbol muere con el proceso
principal, ningún hijo escapa del Job Object) tiene pruebas `windows` propias.
"""

import multiprocessing
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from queued_media_downloader.workers.process_tree_terminator import (
    ProcessTreeTerminationError,
    ProcessTreeTerminator,
)
from tests.doubles.process_tree import (
    PARTIAL_CHUNK,
    TREE_ROLES,
    ProcessTree,
    WatchedProcess,
    attempt_breakaway,
    plain_process,
    platform_process_tree_terminator,
    start_tree,
    wait_for_roles,
    wait_until_all_dead,
)

IS_WINDOWS = sys.platform == "win32"
# En Windows, las pruebas del contrato son pruebas `windows` (campaña final); en
# POSIX se ejecutan siempre con la implementación de grupos de procesos.
on_this_platform: Callable[[Callable[..., None]], Callable[..., None]] = (
    pytest.mark.windows if IS_WINDOWS else (lambda test: test)
)
TreeStarter = Callable[[Path], tuple[ProcessTreeTerminator, ProcessTree]]


def create_terminator() -> ProcessTreeTerminator:
    """La implementación de la plataforma en la que se ejecuta la prueba."""
    return platform_process_tree_terminator()


@pytest.fixture
def started_trees() -> Iterator[TreeStarter]:
    """Arranca árboles registrados; al terminar la prueba, no deja ninguno."""
    created: list[tuple[ProcessTreeTerminator, ProcessTree]] = []

    def start(directory: Path) -> tuple[ProcessTreeTerminator, ProcessTree]:
        directory.mkdir(parents=True, exist_ok=True)
        terminator = create_terminator()
        tree = start_tree(directory, terminator.register_root_process)
        created.append((terminator, tree))
        return terminator, tree

    yield start
    for terminator, tree in created:
        tree.clean_up()
        terminator.release()


@on_this_platform
def test_terminating_the_tree_ends_root_child_and_grandchild(
    tmp_path: Path, started_trees: TreeStarter
) -> None:
    terminator, tree = started_trees(tmp_path)

    terminator.terminate_tree()
    tree.wait_until_dead()

    assert tree.alive_roles() == []


@on_this_platform
def test_terminating_keeps_the_partial_file_intact(
    tmp_path: Path, started_trees: TreeStarter
) -> None:
    terminator, tree = started_trees(tmp_path)

    terminator.terminate_tree()
    tree.wait_until_dead()

    partial_content = tree.part_file.read_bytes()
    assert len(partial_content) >= len(PARTIAL_CHUNK)
    assert set(partial_content) == {PARTIAL_CHUNK[0]}


@on_this_platform
def test_terminating_one_tree_leaves_another_alive(
    tmp_path: Path, started_trees: TreeStarter
) -> None:
    terminator, tree = started_trees(tmp_path / "target")
    _, other_tree = started_trees(tmp_path / "other")

    terminator.terminate_tree()
    tree.wait_until_dead()

    assert tree.alive_roles() == []
    assert other_tree.alive_roles() == ["root", "child", "grandchild"]


@on_this_platform
def test_descendants_of_a_crashed_root_are_terminated(
    tmp_path: Path, started_trees: TreeStarter
) -> None:
    # El worker muere solo; sus descendientes siguen vivos hasta que el pool
    # termina su árbol (ADR-0029, hallazgo 1).
    terminator, tree = started_trees(tmp_path)
    tree.processes["root"].kill()
    tree.root.join(10)

    assert tree.alive_roles() == ["child", "grandchild"]
    terminator.terminate_tree()
    tree.wait_until_dead()
    assert tree.alive_roles() == []


@on_this_platform
def test_terminating_twice_and_releasing_twice_does_not_fail(
    tmp_path: Path, started_trees: TreeStarter
) -> None:
    terminator, tree = started_trees(tmp_path)

    terminator.terminate_tree()
    terminator.terminate_tree()
    terminator.release()
    terminator.release()
    tree.wait_until_dead()

    assert tree.alive_roles() == []


@on_this_platform
def test_root_that_has_not_become_a_tree_root_yet_is_still_terminated(
    tmp_path: Path,
) -> None:
    # El pool podría terminar un worker que aún no ejecutó su arranque.
    context = multiprocessing.get_context("spawn")
    pid_file = tmp_path / "plain.pids"
    process = context.Process(target=plain_process, args=(str(pid_file),), daemon=True)
    process.start()
    watched = WatchedProcess(wait_for_roles(pid_file, ("root",))["root"])
    terminator = create_terminator()
    assert process.pid is not None
    terminator.register_root_process(process.pid)

    try:
        terminator.terminate_tree()
        process.join(10)
        assert not watched.is_alive()
    finally:
        watched.kill()
        watched.close()
        terminator.release()


# --- Garantías propias de Windows (campaña final) ---------------------------------


@pytest.mark.windows
def test_windows_tree_dies_when_its_owner_process_dies(tmp_path: Path) -> None:
    # KILL_ON_JOB_CLOSE: Windows termina el árbol al cerrarse el último handle
    # del Job Object, aunque nadie llame a terminate_tree (UC-05).
    owner = subprocess.Popen(
        [sys.executable, "-m", "tests.doubles.abandoned_tree_owner", str(tmp_path)]
    )
    process_ids = wait_for_roles(tmp_path / "tree.pids", TREE_ROLES)
    watched = [WatchedProcess(process_id) for process_id in process_ids.values()]
    try:
        owner.kill()
        owner.wait()
        assert wait_until_all_dead(watched)
    finally:
        for process in watched:
            process.kill()
            process.close()


@pytest.mark.windows
def test_windows_registered_process_cannot_break_away(tmp_path: Path) -> None:
    # El Job Object no lleva JOB_OBJECT_LIMIT_BREAKAWAY_OK: un descendiente no
    # puede crear un proceso fuera de él con CREATE_BREAKAWAY_FROM_JOB.
    context = multiprocessing.get_context("spawn")
    result_file = tmp_path / "breakaway.txt"
    registered = context.Event()
    attempt = context.Process(
        target=attempt_breakaway, args=(str(result_file), registered), daemon=True
    )
    attempt.start()
    terminator = create_terminator()
    try:
        assert attempt.pid is not None
        terminator.register_root_process(attempt.pid)
        registered.set()
        attempt.join(30)
        assert result_file.read_text(encoding="utf-8") == "denied"
    finally:
        terminator.terminate_tree()
        terminator.release()


@pytest.mark.windows
def test_windows_tree_handle_is_not_inheritable() -> None:
    import ctypes

    terminator = create_terminator()
    flags = ctypes.c_ulong()
    try:
        if sys.platform == "win32":
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            handle = ctypes.c_void_p(vars(terminator)["_job_handle"])
            assert kernel32.GetHandleInformation(handle, ctypes.byref(flags))
        assert flags.value & 0x1 == 0  # HANDLE_FLAG_INHERIT
    finally:
        terminator.release()


@pytest.mark.windows
def test_windows_registration_of_a_missing_process_fails_clearly() -> None:
    terminator = create_terminator()
    try:
        with pytest.raises(ProcessTreeTerminationError):
            terminator.register_root_process(0)
    finally:
        terminator.release()
