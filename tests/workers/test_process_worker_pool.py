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
    FailureReason,
    Job,
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
from queued_media_downloader.workers.process_worker_pool import ProcessWorkerPool
from tests.doubles.fake_media_source import (
    CRASH,
    RAISE,
    FakeMediaSource,
    ScriptedBehavior,
    ScriptKey,
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
            worker_count, functools.partial(FakeMediaSource, script)
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
    pool = ProcessWorkerPool(2, functools.partial(FakeMediaSource, {}))

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
