"""ProcessTreeTerminator que solo anota las llamadas que recibe."""

from dataclasses import dataclass, field


@dataclass
class FakeProcessTreeTerminator:
    """Anota en calls cada llamada, en orden; no termina ningún proceso."""

    calls: list[str] = field(default_factory=list)
    fail_registration: bool = False

    def register_root_process(self, process_id: int) -> None:
        """Anota el registro; falla si así se pidió."""
        from queued_media_downloader.workers.process_tree_terminator import (
            ProcessTreeTerminationError,
        )

        self.calls.append(f"register {process_id}")
        if self.fail_registration:
            message = "Scripted registration failure"
            raise ProcessTreeTerminationError(message)

    def terminate_tree(self) -> None:
        """Anota la terminación."""
        self.calls.append("terminate_tree")

    def release(self) -> None:
        """Anota la liberación."""
        self.calls.append("release")
