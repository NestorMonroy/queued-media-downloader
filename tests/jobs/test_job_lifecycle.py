from itertools import product

import pytest

from queued_media_downloader.jobs import InvalidJobTransitionError, JobStatus
from queued_media_downloader.jobs.job_lifecycle import (
    ensure_transition_allowed,
    is_transition_allowed,
)

# Las once transiciones del diagrama de estados (diseño, Parte 1, §6).
EXPECTED_ALLOWED_TRANSITIONS = {
    (JobStatus.PENDING, JobStatus.RUNNING),
    (JobStatus.PENDING, JobStatus.CANCELLED),
    (JobStatus.RUNNING, JobStatus.COMPLETED),
    (JobStatus.RUNNING, JobStatus.FAILED),
    (JobStatus.RUNNING, JobStatus.CANCELLATION_REQUESTED),
    (JobStatus.RUNNING, JobStatus.PENDING),
    (JobStatus.RUNNING, JobStatus.SKIPPED),
    (JobStatus.CANCELLATION_REQUESTED, JobStatus.CANCELLED),
    (JobStatus.CANCELLATION_REQUESTED, JobStatus.COMPLETED),
    (JobStatus.FAILED, JobStatus.PENDING),
    (JobStatus.CANCELLED, JobStatus.PENDING),
}

ALL_STATUS_PAIRS = list(product(JobStatus, JobStatus))
REJECTED_TRANSITIONS = [
    pair for pair in ALL_STATUS_PAIRS if pair not in EXPECTED_ALLOWED_TRANSITIONS
]


def describe(pair: tuple[JobStatus, JobStatus]) -> str:
    return f"{pair[0].value}->{pair[1].value}"


@pytest.mark.parametrize("transition", ALL_STATUS_PAIRS, ids=describe)
def test_transition_is_allowed_only_when_it_appears_in_the_state_diagram(
    transition: tuple[JobStatus, JobStatus],
) -> None:
    current_status, target_status = transition

    allowed = is_transition_allowed(current_status, target_status)

    assert allowed == (transition in EXPECTED_ALLOWED_TRANSITIONS)


@pytest.mark.parametrize("transition", REJECTED_TRANSITIONS, ids=describe)
def test_rejected_transition_raises_an_error_naming_both_statuses(
    transition: tuple[JobStatus, JobStatus],
) -> None:
    current_status, target_status = transition

    with pytest.raises(InvalidJobTransitionError) as raised:
        ensure_transition_allowed(current_status, target_status)

    assert current_status.value in str(raised.value)
    assert target_status.value in str(raised.value)


def test_completed_and_skipped_are_terminal_statuses() -> None:
    for terminal_status in (JobStatus.COMPLETED, JobStatus.SKIPPED):
        assert not any(
            is_transition_allowed(terminal_status, target_status)
            for target_status in JobStatus
        )
