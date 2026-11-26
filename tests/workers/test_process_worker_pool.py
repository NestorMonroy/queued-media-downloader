import functools
import logging
import multiprocessing
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import replace
from pathlib import Path

import pytest

from queued_media_downloader.jobs import (
    DownloadOptions,
    DownloadProgressed,
    FailureReason,
    Job,
    JobCancelled,
    JobCompleted,
    JobFailed,
    JobId,
    JobKind,
    JobStarted,
    JobStatus,
    MediaKey,
    SingleMediaFound,
)
from queued_media_downloader.workers import (
    NoIdleWorkerError,
    WorkerMessage,
    WorkerPool,
)
from queued_media_downloader.workers.process_tree_terminator import (
    ProcessTreeTerminationError,
)
from queued_media_downloader.workers.process_worker_pool import ProcessWorkerPool
from tests.doubles.fake_media_source import (
    CRASH,
    RAISE,
    FakeMediaSource,
    ProgressForever,
    ScriptedBehavior,
    ScriptKey,
    SpawnChild,
)
from tests.doubles.fake_process_tree_terminator import FakeProcessTreeTerminator
from tests.doubles.process_tree import (
    WatchedProcess,
    platform_process_tree_terminator,
    wait_for_roles,
    wait_until_all_dead,
)

COLLECT_TIMEOUT_SECONDS = 30.0
SINGLE_MEDIA_FOUND = SingleMediaFound(
    media_key=MediaKey(extractor_key="Generic", media_id="a"), title="a"
)
COMPLETED = JobCompleted(output_path="a.mp4")


def stored_job(job_id: int, url: str, kind: JobKind = JobKind.EXPANSION) -> Job:
    """Job ya guardado y listo para ejecutarse."""
    job = Job.new_expansion(
        url,
        DownloadOptions(
            format_selector="b",
            download_directory=Path("downloads"),
            output_template="%(id)s.%(ext)s",
            audio_only=False,
        ),
    )
    return replace(job, job_id=JobId(job_id), kind=kind, status=JobStatus.RUNNING)


@pytest.fixture
def start_pool() -> Iterator[
    Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool]
]:
    """Arranca pools con un FakeMediaSource y los apaga al terminar la prueba."""
    started_pools: list[ProcessWorkerPool] = []

    def start(
        worker_count: int, script: Mapping[ScriptKey, ScriptedBehavior]
    ) -> WorkerPool:
        pool = ProcessWorkerPool(
            worker_count,
            functools.partial(FakeMediaSource, script),
            platform_process_tree_terminator,
        )
        started_pools.append(pool)
        return pool

    yield start
    for pool in started_pools:
        pool.shut_down()


def collect_until_final(pool: WorkerPool, job_ids: set[JobId]) -> list[WorkerMessage]:
    """Recoge mensajes hasta que cada job de job_ids publique su evento final."""
    final_event_types = (SingleMediaFound, JobCompleted, JobFailed)
    collected: list[WorkerMessage] = []
    pending_job_ids = set(job_ids)
    deadline = time.monotonic() + COLLECT_TIMEOUT_SECONDS
    while pending_job_ids and time.monotonic() < deadline:
        for message in pool.collect_events(timeout_seconds=0.2):
            collected.append(message)
            if isinstance(message.job_event, final_event_types):
                pending_job_ids.discard(message.job_id)
    assert not pending_job_ids, f"No final event for {pending_job_ids}"
    return collected


def test_expansion_job_publishes_started_and_its_events_with_its_job_id(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
) -> None:
    pool = start_pool(1, {("expand", "https://a"): [SINGLE_MEDIA_FOUND]})

    pool.submit(stored_job(7, "https://a"))
    messages = collect_until_final(pool, {JobId(7)})

    assert [(m.job_id, m.job_event) for m in messages] == [
        (JobId(7), JobStarted()),
        (JobId(7), SINGLE_MEDIA_FOUND),
    ]


def test_download_job_is_run_with_download(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
) -> None:
    pool = start_pool(1, {("download", "https://a"): [COMPLETED]})

    pool.submit(stored_job(1, "https://a", kind=JobKind.DOWNLOAD))
    messages = collect_until_final(pool, {JobId(1)})

    assert messages[-1].job_event == COMPLETED


def test_messages_of_a_worker_are_numbered_in_order(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
) -> None:
    pool = start_pool(1, {("expand", "https://a"): [SINGLE_MEDIA_FOUND]})

    pool.submit(stored_job(1, "https://a"))
    first_job_messages = collect_until_final(pool, {JobId(1)})
    pool.submit(stored_job(2, "https://a"))
    second_job_messages = collect_until_final(pool, {JobId(2)})

    sequence_numbers = [
        m.sequence_number for m in first_job_messages + second_job_messages
    ]
    assert sequence_numbers == [1, 2, 3, 4]


def test_each_worker_runs_one_job_at_a_time(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
) -> None:
    pool = start_pool(2, {("download", "https://a"): [COMPLETED]})
    assert pool.count_idle_workers() == 2

    pool.submit(stored_job(1, "https://a", kind=JobKind.DOWNLOAD))
    pool.submit(stored_job(2, "https://a", kind=JobKind.DOWNLOAD))
    assert pool.count_idle_workers() == 0
    with pytest.raises(NoIdleWorkerError):
        pool.submit(stored_job(3, "https://a", kind=JobKind.DOWNLOAD))

    collect_until_final(pool, {JobId(1), JobId(2)})
    assert pool.count_idle_workers() == 2


def test_unexpected_exception_fails_the_job_and_keeps_the_worker(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
) -> None:
    pool = start_pool(
        1,
        {
            ("download", "https://raises"): RAISE,
            ("download", "https://a"): [COMPLETED],
        },
    )

    pool.submit(stored_job(1, "https://raises", kind=JobKind.DOWNLOAD))
    [_, failure] = collect_until_final(pool, {JobId(1)})
    pool.submit(stored_job(2, "https://a", kind=JobKind.DOWNLOAD))
    next_job_messages = collect_until_final(pool, {JobId(2)})

    assert isinstance(failure.job_event, JobFailed)
    assert failure.job_event.failure_reason is FailureReason.UNKNOWN
    assert "Scripted failure" in failure.job_event.failure_message
    assert next_job_messages[0].worker_id == failure.worker_id


def test_crashed_worker_fails_its_job_and_is_replaced(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
) -> None:
    pool = start_pool(
        1,
        {
            ("download", "https://crashes"): CRASH,
            ("download", "https://a"): [COMPLETED],
        },
    )

    pool.submit(stored_job(1, "https://crashes", kind=JobKind.DOWNLOAD))
    crash_messages = collect_until_final(pool, {JobId(1)})
    pool.submit(stored_job(2, "https://a", kind=JobKind.DOWNLOAD))
    next_job_messages = collect_until_final(pool, {JobId(2)})

    failure = crash_messages[-1]
    assert isinstance(failure.job_event, JobFailed)
    assert failure.job_event.failure_reason is FailureReason.WORKER_CRASHED
    assert next_job_messages[-1].job_event == COMPLETED
    assert next_job_messages[-1].worker_id != failure.worker_id


def test_shut_down_stops_every_worker_process() -> None:
    pool = ProcessWorkerPool(
        2, functools.partial(FakeMediaSource, {}), platform_process_tree_terminator
    )

    pool.shut_down()

    assert multiprocessing.active_children() == []


def test_log_records_of_a_worker_reach_the_logging_of_the_main_process(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="tests.doubles.fake_media_source")
    pool = start_pool(1, {("download", "https://a"): [COMPLETED]})

    pool.submit(stored_job(1, "https://a", kind=JobKind.DOWNLOAD))
    collect_until_final(pool, {JobId(1)})

    expected_message = "Performing download https://a"
    deadline = time.monotonic() + COLLECT_TIMEOUT_SECONDS
    while expected_message not in caplog.messages and time.monotonic() < deadline:
        time.sleep(0.05)
    assert expected_message in caplog.messages


def watch_child(pid_file: Path) -> WatchedProcess:
    """El hijo que lanzó el job, seguido por handle."""
    return WatchedProcess(wait_for_roles(pid_file, ("child",))["child"])


def test_children_of_a_crashed_worker_are_terminated_before_replacing_it(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
    tmp_path: Path,
) -> None:
    # Sin terminar su árbol, el ffmpeg de un worker caído seguiría escribiendo
    # mientras el reintento escribe los mismos archivos (ADR-0029, hallazgo 1).
    pid_file = tmp_path / "child.pids"
    pool = start_pool(
        1, {("download", "https://crashes"): SpawnChild(str(pid_file), then_crash=True)}
    )
    pool.submit(stored_job(1, "https://crashes", kind=JobKind.DOWNLOAD))
    child = watch_child(pid_file)

    try:
        crash_messages = collect_until_final(pool, {JobId(1)})

        assert not child.is_alive()
        failure = crash_messages[-1].job_event
        assert isinstance(failure, JobFailed)
        assert failure.failure_reason is FailureReason.WORKER_CRASHED
        assert pool.count_idle_workers() == 1
    finally:
        child.kill()
        child.close()


def test_terminating_the_worker_running_a_job_ends_its_tree_and_replaces_it(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
    tmp_path: Path,
) -> None:
    pid_file = tmp_path / "child.pids"
    pool = start_pool(
        1,
        {
            ("download", "https://hangs"): SpawnChild(str(pid_file), then_crash=False),
            ("download", "https://a"): [COMPLETED],
        },
    )
    pool.submit(stored_job(1, "https://hangs", kind=JobKind.DOWNLOAD))
    child = watch_child(pid_file)

    try:
        terminated = pool.terminate_worker_running(JobId(1))

        assert terminated
        assert wait_until_all_dead([child])
        assert pool.count_idle_workers() == 1
        pool.submit(stored_job(2, "https://a", kind=JobKind.DOWNLOAD))
        assert collect_until_final(pool, {JobId(2)})[-1].job_event == COMPLETED
    finally:
        child.kill()
        child.close()


def test_terminating_a_job_no_worker_is_running_changes_nothing(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
) -> None:
    pool = start_pool(2, {})

    assert not pool.terminate_worker_running(JobId(99))
    assert pool.count_idle_workers() == 2


def test_shut_down_terminates_the_tree_of_a_worker_that_does_not_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid_file = tmp_path / "child.pids"
    script: dict[ScriptKey, ScriptedBehavior] = {
        ("download", "https://hangs"): SpawnChild(str(pid_file), then_crash=False)
    }
    monkeypatch.setattr(
        "queued_media_downloader.workers.process_worker_pool.SHUT_DOWN_TIMEOUT_SECONDS",
        0.5,
    )
    pool = ProcessWorkerPool(
        1, functools.partial(FakeMediaSource, script), platform_process_tree_terminator
    )
    pool.submit(stored_job(1, "https://hangs", kind=JobKind.DOWNLOAD))
    child = watch_child(pid_file)

    try:
        pool.shut_down()

        assert wait_until_all_dead([child])
        assert multiprocessing.active_children() == []
    finally:
        child.kill()
        child.close()


def test_each_worker_is_registered_before_any_job_and_released_at_the_end() -> None:
    terminators: list[FakeProcessTreeTerminator] = []

    def create_fake_terminator() -> FakeProcessTreeTerminator:
        terminators.append(FakeProcessTreeTerminator())
        return terminators[-1]

    pool = ProcessWorkerPool(
        2, functools.partial(FakeMediaSource, {}), create_fake_terminator
    )
    pool.shut_down()

    assert len(terminators) == 2
    for terminator in terminators:
        assert terminator.calls[0].startswith("register ")
        assert terminator.calls[-1] == "release"


def test_failed_registration_stops_the_pool_without_leaving_workers() -> None:
    def create_failing_terminator() -> FakeProcessTreeTerminator:
        return FakeProcessTreeTerminator(fail_registration=True)

    with pytest.raises(ProcessTreeTerminationError):
        ProcessWorkerPool(
            2, functools.partial(FakeMediaSource, {}), create_failing_terminator
        )

    assert multiprocessing.active_children() == []


def test_cancellation_stops_the_job_at_its_next_event_and_keeps_the_worker(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
) -> None:
    # UC-05, pasos 4 a 6: la bandera se ve en el siguiente avance publicado.
    pool = start_pool(
        1,
        {
            ("download", "https://long"): ProgressForever(),
            ("download", "https://a"): [COMPLETED],
        },
    )
    pool.submit(stored_job(1, "https://long", kind=JobKind.DOWNLOAD))
    first_progress = wait_for_event(pool, JobId(1), DownloadProgressed)

    pool.request_cancellation(JobId(1))
    cancelled = wait_for_event(pool, JobId(1), JobCancelled)

    assert cancelled.worker_id == first_progress.worker_id
    assert pool.count_idle_workers() == 1
    pool.submit(stored_job(2, "https://a", kind=JobKind.DOWNLOAD))
    next_job = collect_until_final(pool, {JobId(2)})[-1]
    assert next_job.job_event == COMPLETED
    assert next_job.worker_id == cancelled.worker_id


def test_cancelling_a_job_no_worker_is_running_has_no_effect(
    start_pool: Callable[[int, Mapping[ScriptKey, ScriptedBehavior]], WorkerPool],
) -> None:
    pool = start_pool(1, {("download", "https://a"): [COMPLETED]})

    pool.request_cancellation(JobId(99))
    pool.submit(stored_job(1, "https://a", kind=JobKind.DOWNLOAD))

    assert collect_until_final(pool, {JobId(1)})[-1].job_event == COMPLETED


def wait_for_event(
    pool: WorkerPool, job_id: JobId, event_type: type[object]
) -> WorkerMessage:
    """Recoge mensajes hasta el primero de event_type para job_id."""
    deadline = time.monotonic() + COLLECT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        for message in pool.collect_events(timeout_seconds=0.2):
            if message.job_id == job_id and isinstance(message.job_event, event_type):
                return message
    pytest.fail(f"No {event_type.__name__} for job {job_id}")


def test_worker_is_recycled_after_max_jobs_per_worker() -> None:
    # UC-03 A6: termina limpiamente al acabar su job y un reemplazo sigue.
    script: dict[ScriptKey, ScriptedBehavior] = {
        ("download", f"https://{n}"): [COMPLETED] for n in range(3)
    }
    pool = ProcessWorkerPool(
        1,
        functools.partial(FakeMediaSource, script),
        platform_process_tree_terminator,
        max_jobs_per_worker=2,
    )
    try:
        worker_ids = []
        for n in range(3):
            pool.submit(stored_job(n + 1, f"https://{n}", kind=JobKind.DOWNLOAD))
            worker_ids.append(collect_until_final(pool, {JobId(n + 1)})[-1].worker_id)

        assert worker_ids[0] == worker_ids[1]
        assert worker_ids[2] != worker_ids[0]
        assert len(multiprocessing.active_children()) == 1
    finally:
        pool.shut_down()


class FlakyTerminators:
    """Fábrica de terminadores falsos: el registro falla en los intentos dados.

    Simula un worker que muere mientras se asocia a su Job Object.
    """

    def __init__(self, failing_attempts: set[int]) -> None:
        self.failing_attempts = failing_attempts
        self.created: list[FakeProcessTreeTerminator] = []

    def __call__(self) -> FakeProcessTreeTerminator:
        attempt = len(self.created) + 1
        self.created.append(
            FakeProcessTreeTerminator(
                fail_registration=attempt in self.failing_attempts
            )
        )
        return self.created[-1]


def test_a_worker_that_dies_while_registering_is_started_again() -> None:
    terminators = FlakyTerminators(failing_attempts={1})

    pool = ProcessWorkerPool(1, functools.partial(FakeMediaSource, {}), terminators)
    idle_workers = pool.count_idle_workers()
    pool.shut_down()

    assert idle_workers == 1
    # El intento fallido se liberó; el nuevo worker, también al apagar.
    assert [t.calls[-1] for t in terminators.created] == ["release", "release"]
    assert multiprocessing.active_children() == []


def test_a_replacement_that_cannot_register_stops_the_pool_cleanly() -> None:
    # El primer worker arranca; todos los intentos de sustituirlo fallan.
    terminators = FlakyTerminators(failing_attempts=set(range(2, 10)))
    pool = ProcessWorkerPool(
        1,
        functools.partial(FakeMediaSource, {("download", "https://crashes"): CRASH}),
        terminators,
    )
    pool.submit(stored_job(1, "https://crashes", kind=JobKind.DOWNLOAD))

    with pytest.raises(ProcessTreeTerminationError):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            pool.collect_events(0.1)
    pool.shut_down(immediately=True)

    assert multiprocessing.active_children() == []
    assert all(t.calls[-1] == "release" for t in terminators.created)
