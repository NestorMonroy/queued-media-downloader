"""Instrucciones que el proceso principal envía a un worker."""

from dataclasses import dataclass

from queued_media_downloader.jobs import Job


@dataclass(frozen=True, slots=True)
class RunJob:
    """Ejecutar el job: expandirlo o descargarlo según su tipo."""

    job: Job


@dataclass(frozen=True, slots=True)
class ShutDown:
    """Terminar el worker cuando acabe el job en curso."""


WorkerInstruction = RunJob | ShutDown
