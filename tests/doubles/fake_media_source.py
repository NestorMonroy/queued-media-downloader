"""MediaSource que publica una secuencia de job events predefinida."""

import os
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Literal

from queued_media_downloader.jobs import Job, JobEvent
from queued_media_downloader.media_extraction import Publish


class ScriptedFailure(Enum):
    """Fallos que el guion puede pedir en lugar de publicar job events."""

    # El proceso del worker termina de golpe, como si se cayera.
    CRASH = "crash"
    # La MediaSource lanza una excepción que no debería escaparse.
    RAISE = "raise"


CRASH = ScriptedFailure.CRASH
RAISE = ScriptedFailure.RAISE

ScriptedBehavior = Sequence[JobEvent] | ScriptedFailure
ScriptKey = tuple[Literal["expand", "download"], str]


class FakeMediaSource:
    """Publica, para cada método y URL, lo que indica el guion.

    Se crea en el proceso del worker con functools.partial(FakeMediaSource,
    script), que se puede enviar con pickle.
    """

    def __init__(self, script: Mapping[ScriptKey, ScriptedBehavior]) -> None:
        """Guarda el guion; una URL sin guion no publica nada."""
        self._script = script

    def expand(self, job: Job, publish: Publish) -> None:
        """Sigue el guion de ("expand", url)."""
        self._perform(("expand", job.url), publish)

    def download(self, job: Job, publish: Publish) -> None:
        """Sigue el guion de ("download", url)."""
        self._perform(("download", job.url), publish)

    def _perform(self, script_key: ScriptKey, publish: Publish) -> None:
        """Publica los job events del guion, o se cae o lanza si así se indica."""
        behavior = self._script.get(script_key, ())
        if behavior is ScriptedFailure.CRASH:
            os._exit(3)
        if isinstance(behavior, ScriptedFailure):
            message = f"Scripted failure for {script_key}"
            raise RuntimeError(message)
        for job_event in behavior:
            publish(job_event)
