"""MediaSource que publica una secuencia de job events predefinida."""

import logging
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal, NoReturn

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


@dataclass(frozen=True)
class SpawnChild:
    """Lanza un proceso hijo, como yt-dlp lanza ffmpeg, y después se cae o se cuelga.

    El PID del hijo se anota en pid_file para que la prueba lo siga.
    """

    pid_file: str
    then_crash: bool


ScriptedBehavior = Sequence[JobEvent] | ScriptedFailure | SpawnChild

logger = logging.getLogger(__name__)
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
        logger.info("Performing %s %s", *script_key)
        behavior = self._script.get(script_key, ())
        if isinstance(behavior, SpawnChild):
            _spawn_child_then(behavior)
        if behavior is ScriptedFailure.CRASH:
            os._exit(3)
        if isinstance(behavior, ScriptedFailure):
            message = f"Scripted failure for {script_key}"
            raise RuntimeError(message)
        for job_event in behavior:
            publish(job_event)


def _spawn_child_then(behavior: SpawnChild) -> NoReturn:
    """Lanza el hijo con Popen sin creationflags y se cae o se cuelga."""
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    Path(behavior.pid_file).write_text(f"child {child.pid}\n", encoding="utf-8")
    if behavior.then_crash:
        os._exit(3)
    while True:
        time.sleep(1)
