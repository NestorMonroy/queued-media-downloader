import signal

import pytest

from queued_media_downloader.command_line.console_interruption import (
    InterruptionRequest,
    handling_interruptions,
)


def test_first_ctrl_c_only_asks_to_stop() -> None:
    interruption_request = InterruptionRequest()

    interruption_request.handle_signal(signal.SIGINT, None)

    assert interruption_request()


def test_second_ctrl_c_stops_at_once() -> None:
    interruption_request = InterruptionRequest()
    interruption_request.handle_signal(signal.SIGINT, None)

    with pytest.raises(KeyboardInterrupt):
        interruption_request.handle_signal(signal.SIGINT, None)


def test_later_ctrl_c_never_interrupt_the_immediate_stop(
    capsys: pytest.CaptureFixture[str],
) -> None:
    interruption_request = InterruptionRequest()
    interruption_request.handle_signal(signal.SIGINT, None)
    with pytest.raises(KeyboardInterrupt):
        interruption_request.handle_signal(signal.SIGINT, None)

    for _ in range(3):
        interruption_request.handle_signal(signal.SIGINT, None)

    assert capsys.readouterr().out.count("Already stopping") == 1


def test_ctrl_c_stays_ignored_until_an_interrupted_run_exits() -> None:
    original_handler = signal.getsignal(signal.SIGINT)
    try:
        with handling_interruptions() as interruption_request:
            interruption_request.handle_signal(signal.SIGINT, None)

        assert signal.getsignal(signal.SIGINT) is signal.SIG_IGN
    finally:
        signal.signal(signal.SIGINT, original_handler)


def test_a_run_without_ctrl_c_gives_back_the_previous_handler() -> None:
    original_handler = signal.getsignal(signal.SIGINT)

    with handling_interruptions():
        pass

    assert signal.getsignal(signal.SIGINT) is original_handler
