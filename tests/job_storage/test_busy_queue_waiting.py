import sqlite3

import pytest

from queued_media_downloader.job_storage import BusyQueueWaiting, JobStoreLockedError


class FailingTimes:
    """Operación que falla con los errores dados y luego devuelve "done"."""

    def __init__(self, *errors: Exception) -> None:
        self._errors = list(errors)
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self._errors:
            raise self._errors.pop(0)
        return "done"


def test_a_locked_queue_is_retried_until_it_is_free_and_reported_once() -> None:
    reports: list[None] = []
    operation = FailingTimes(
        JobStoreLockedError("database is locked"),
        sqlite3.OperationalError("database is locked"),
    )

    result = BusyQueueWaiting(lambda: reports.append(None)).run(operation)

    assert result == "done"
    assert operation.calls == 3
    assert len(reports) == 1


def test_each_new_wait_is_reported() -> None:
    reports: list[None] = []
    waiting = BusyQueueWaiting(lambda: reports.append(None))

    waiting.run(FailingTimes(JobStoreLockedError("database is locked")))
    waiting.run(FailingTimes(JobStoreLockedError("database is locked")))

    assert len(reports) == 2


def test_other_database_errors_are_not_retried() -> None:
    operation = FailingTimes(sqlite3.OperationalError("disk I/O error"))

    with pytest.raises(sqlite3.OperationalError, match="disk I/O error"):
        BusyQueueWaiting(lambda: None).run(operation)

    assert operation.calls == 1
