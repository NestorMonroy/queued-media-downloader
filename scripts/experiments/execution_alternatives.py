"""Experimentos comparativos de las alternativas de ejecución (instrucción 2.4.0).

Cada experimento responde una pregunta concreta de la cualificación de ADR-0008
con entradas controladas: un servidor HTTP local en 127.0.0.1 que limita su
velocidad o deja de responder, directorios temporales propios y, en el último,
una instalación aislada del producto. No usa red externa, ni la cola, el
estado, las descargas o la configuración reales. No es código de producción:
no lo importa el paquete ni lo ejecuta pytest.

Experimentos:
- startup: coste de arrancar un proceso (contexto spawn, como ProcessWorkerPool)
  hasta tener yt-dlp importado y un YoutubeDL creado; coste de crear un
  YoutubeDL en un intérprete ya caliente.
- sequential / concurrent: N descargas iguales, en secuencia (baseline), con
  hilos, con un proceso por job y con un pool de procesos ya arrancado; tiempo
  total y memoria máxima del árbol de procesos.
- blocked_cancellation: un servidor que no responde; latencia de la cancelación
  cooperativa (hook de progreso) en un hilo frente a terminar un proceso.
- descendants: un hijo externo (como ffmpeg) lanzado desde un hilo o desde un
  proceso líder de su grupo; qué sobrevive a la cancelación.
- crash_isolation: un fallo nativo (os.abort) en un hilo frente a uno en un
  proceso: qué ocurre con el otro job.
- event_loop: retardo máximo de un event loop de asyncio con una descarga de
  yt-dlp ejecutada dentro de la corrutina frente a asyncio.to_thread.
- event_overhead: coste por mensaje de una cola entre procesos (spawn) frente a
  una llamada en el mismo proceso.
- memory_growth: memoria de un proceso que ejecuta descargas sucesivas.
- consumer_without_cli: encolar, ejecutar, consultar, cancelar y recuperar con
  los componentes del producto sin importar command_line.

Uso, desde la raíz del repositorio:

    uv run python scripts/experiments/execution_alternatives.py --output RUTA

Solo para Linux: lee la memoria de /proc y usa grupos de procesos POSIX.
"""

import argparse
import asyncio
import concurrent.futures
import contextlib
import functools
import http.server
import json
import multiprocessing
import os
import platform
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import yt_dlp

CHUNK = 65_536
REPETITIONS = 3
CONCURRENT_JOBS = 4
MEDIA_SIZE = 1_048_576
BYTES_PER_SECOND = 2_097_152
STALL_SECONDS = 30.0
SOCKET_TIMEOUT_SECONDS = 3.0
CANCEL_AFTER_SECONDS = 0.5


class ThrottledMediaHandler(http.server.BaseHTTPRequestHandler):
    """Sirve /media-N.mp4 a BYTES_PER_SECOND; /stall acepta y no responde."""

    def do_HEAD(self) -> None:
        """Cabeceras del medio."""
        self._headers()

    def do_GET(self) -> None:
        """Cuerpo limitado en velocidad, o ninguna respuesta en /stall."""
        if self.path.startswith("/stall"):
            time.sleep(STALL_SECONDS)
            return
        self._headers()
        sent = 0
        while sent < MEDIA_SIZE:
            started = time.monotonic()
            try:
                self.wfile.write(b"\0" * CHUNK)
            except (BrokenPipeError, ConnectionResetError):
                return
            sent += CHUNK
            elapsed = time.monotonic() - started
            time.sleep(max(0.0, CHUNK / BYTES_PER_SECOND - elapsed))

    def _headers(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(MEDIA_SIZE))
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        """Silencia el registro."""


@contextlib.contextmanager
def media_server() -> Iterator[str]:
    """Arranca el servidor local y devuelve su URL base."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), ThrottledMediaHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def ydl_parameters(
    directory: Path, hook: Callable[[dict[str, Any]], None] | None = None
) -> dict[str, Any]:
    """Parámetros mínimos y comunes a todas las alternativas."""
    parameters: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "cachedir": False,
        # Un nombre único por descarga: las alternativas concurrentes no
        # comparten archivos.
        "outtmpl": str(directory / f"{uuid.uuid4().hex}.%(ext)s"),
        "socket_timeout": SOCKET_TIMEOUT_SECONDS,
        "retries": 0,
        "fragment_retries": 0,
        "extractor_retries": 0,
        "overwrites": True,
    }
    if hook is not None:
        parameters["progress_hooks"] = [hook]
    return parameters


def download(url: str, directory: Path) -> None:
    """Una descarga completa con un YoutubeDL nuevo, como hace cada job."""
    with yt_dlp.YoutubeDL(ydl_parameters(directory)) as ydl:
        ydl.download([url])


def rss_kib(pid: int) -> int:
    """VmRSS de un proceso en KiB; 0 si ya no existe."""
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (FileNotFoundError, ProcessLookupError):
        return 0
    return 0


def descendants(pid: int) -> list[int]:
    """PIDs descendientes de pid (lectura de /proc)."""
    children: dict[int, list[int]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
        except (FileNotFoundError, ProcessLookupError, IndexError):
            continue
        children.setdefault(int(fields[1]), []).append(int(entry.name))
    found: list[int] = []
    pending = [pid]
    while pending:
        current = pending.pop()
        for child in children.get(current, []):
            found.append(child)
            pending.append(child)
    return found


class TreeMemorySampler:
    """Muestrea la memoria del árbol de este proceso cada 20 ms."""

    def __init__(self) -> None:
        """Sin muestras todavía."""
        self.peak_kib = 0
        self.peak_processes = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def __enter__(self) -> "TreeMemorySampler":
        """Empieza a muestrear."""
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        """Deja de muestrear."""
        self._stop.set()
        self._thread.join()

    def _sample(self) -> None:
        while not self._stop.is_set():
            tree = [os.getpid(), *descendants(os.getpid())]
            self.peak_kib = max(self.peak_kib, sum(rss_kib(pid) for pid in tree))
            self.peak_processes = max(self.peak_processes, len(tree))
            self._stop.wait(0.02)


def summary(values: list[float]) -> dict[str, float]:
    """Mínimo, mediana y máximo observados, redondeados."""
    return {
        "min": round(min(values), 3),
        "median": round(statistics.median(values), 3),
        "max": round(max(values), 3),
    }


# --- Procesos hijos (funciones de módulo: el contexto spawn las importa) ---


def startup_child(ready: Any) -> None:
    """Importa yt-dlp y crea un YoutubeDL; informa de los tiempos."""
    imported_at = time.perf_counter()
    import yt_dlp as library

    with library.YoutubeDL({"quiet": True}):
        pass
    ready.put({"import_and_create_seconds": time.perf_counter() - imported_at})


def download_child(url: str, directory: str) -> None:
    """Un proceso por job."""
    download(url, Path(directory))


def pool_worker(instructions: Any, results: Any) -> None:
    """Worker persistente: descarga lo que llega hasta recibir None."""
    while (instruction := instructions.get()) is not None:
        url, directory = instruction
        download(url, Path(directory))
        results.put(rss_kib(os.getpid()))


def blocked_child(url: str, directory: str) -> None:
    """Descarga desde un servidor que no responde."""
    with contextlib.suppress(yt_dlp.utils.DownloadError):
        download(url, Path(directory))


def leader_with_external_child(pids: Any) -> None:
    """Líder de su grupo de procesos que lanza un hijo externo (como ffmpeg)."""
    os.setsid()
    child = subprocess.Popen(["sleep", "60"])
    pids.put(child.pid)
    child.wait()


def message_sender(messages: Any, count: int) -> None:
    """Envía count mensajes pequeños, como los job events de progreso."""
    for index in range(count):
        messages.put(("progress", index, 1024 * index, None))
    messages.put(None)


def successive_downloads_child(
    url: str, directory: str, jobs: int, results: Any
) -> None:
    """Descargas sucesivas en un mismo proceso; memoria tras cada una."""
    for _ in range(jobs):
        download(url, Path(directory))
        results.put(rss_kib(os.getpid()))
    results.put(None)


# --- Experimentos ---


def startup_experiment(context: Any) -> dict[str, Any]:
    """Coste de arranque de un proceso con yt-dlp frente a un YoutubeDL caliente."""
    ready_seconds, inside_seconds = [], []
    for _ in range(5):
        queue = context.Queue()
        started = time.perf_counter()
        process = context.Process(target=startup_child, args=(queue,))
        process.start()
        report = queue.get(timeout=60)
        ready_seconds.append(time.perf_counter() - started)
        inside_seconds.append(report["import_and_create_seconds"])
        process.join()
    warm = []
    for _ in range(20):
        started = time.perf_counter()
        with yt_dlp.YoutubeDL({"quiet": True}):
            pass
        warm.append(time.perf_counter() - started)
    return {
        "process_ready_seconds": summary(ready_seconds),
        "import_and_create_inside_child_seconds": summary(inside_seconds),
        "warm_youtubedl_creation_seconds": summary(warm),
    }


def run_sequential(urls: list[str], directory: Path, _context: Any) -> None:
    """Baseline: una descarga detrás de otra en este proceso."""
    for url in urls:
        download(url, directory)


def run_threads(urls: list[str], directory: Path, _context: Any) -> None:
    """Un hilo por descarga, cada uno con su YoutubeDL."""
    with concurrent.futures.ThreadPoolExecutor(len(urls)) as executor:
        list(executor.map(lambda url: download(url, directory), urls))


def run_process_per_job(urls: list[str], directory: Path, context: Any) -> None:
    """Un proceso nuevo por descarga, arranque incluido."""
    processes = [
        context.Process(target=download_child, args=(url, str(directory)))
        for url in urls
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join()


def start_warm_pool(
    base: str, directory: Path, context: Any
) -> tuple[list[Any], Any, Any]:
    """Arranca los workers y espera a que cada uno haya hecho una descarga."""
    instructions, results = context.Queue(), context.Queue()
    pool = [
        context.Process(target=pool_worker, args=(instructions, results))
        for _ in range(CONCURRENT_JOBS)
    ]
    for process in pool:
        process.start()
    for _ in pool:
        instructions.put((f"{base}/warm.mp4", str(directory)))
    for _ in pool:
        results.get(timeout=60)
    return pool, instructions, results


@contextlib.contextmanager
def warm_process_pool(
    base: str, directory: Path, context: Any
) -> Iterator[Callable[[list[str], Path, Any], None]]:
    """Pool de CONCURRENT_JOBS procesos ya arrancados y calentados."""
    pool, instructions, results = start_warm_pool(base, directory, context)

    def run(urls: list[str], target: Path, _context: Any) -> None:
        for url in urls:
            instructions.put((url, str(target)))
        for _ in urls:
            results.get(timeout=60)

    try:
        yield run
    finally:
        for _ in pool:
            instructions.put(None)
        for process in pool:
            process.join()


VARIANTS: dict[str, Callable[[list[str], Path, Any], None]] = {
    "sequential": run_sequential,
    "threads": run_threads,
    "process_per_job": run_process_per_job,
}


def run_variant(name: str, base: str, work: Path, context: Any) -> dict[str, Any]:
    """N descargas con la alternativa name; tiempo y memoria del árbol."""
    urls = [f"{base}/media-{index}.mp4" for index in range(CONCURRENT_JOBS)]
    directory = work / name
    directory.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack:
        run = (
            stack.enter_context(warm_process_pool(base, directory, context))
            if name == "process_pool"
            else VARIANTS[name]
        )
        with TreeMemorySampler() as sampler:
            started = time.perf_counter()
            run(urls, directory, context)
            elapsed = time.perf_counter() - started
    return {
        "seconds": elapsed,
        "peak_tree_rss_mib": round(sampler.peak_kib / 1024, 1),
        "peak_processes": sampler.peak_processes,
    }


def concurrency_experiment(base: str, work: Path, context: Any) -> dict[str, Any]:
    """Secuencial (baseline) frente a hilos, proceso por job y pool caliente."""
    variants = ("sequential", "threads", "process_per_job", "process_pool")
    runs: dict[str, list[dict[str, Any]]] = {name: [] for name in variants}
    for repetition in range(REPETITIONS):
        for name in variants:
            runs[name].append(run_variant(name, base, work / str(repetition), context))
    return {
        "jobs": CONCURRENT_JOBS,
        "media_bytes": MEDIA_SIZE,
        "server_bytes_per_second_per_connection": BYTES_PER_SECOND,
        "results": {
            name: {
                "seconds": summary([run["seconds"] for run in values]),
                "peak_tree_rss_mib": summary(
                    [run["peak_tree_rss_mib"] for run in values]
                ),
                "peak_processes": max(run["peak_processes"] for run in values),
            }
            for name, values in runs.items()
        },
    }


def blocked_cancellation_experiment(
    base: str, work: Path, context: Any
) -> dict[str, Any]:
    """Cancelar una descarga bloqueada: hilo cooperativo frente a proceso."""
    cancelled = threading.Event()
    hook_calls = 0

    def hook(_status: dict[str, Any]) -> None:
        nonlocal hook_calls
        hook_calls += 1
        if cancelled.is_set():
            raise yt_dlp.utils.DownloadCancelled

    def blocked_in_thread() -> None:
        with (
            contextlib.suppress(
                yt_dlp.utils.DownloadError, yt_dlp.utils.DownloadCancelled
            ),
            yt_dlp.YoutubeDL(ydl_parameters(work, hook)) as ydl,
        ):
            ydl.download([f"{base}/stall"])

    with concurrent.futures.ThreadPoolExecutor(1) as executor:
        future = executor.submit(blocked_in_thread)
        time.sleep(CANCEL_AFTER_SECONDS)
        requested = time.perf_counter()
        cancelled.set()
        future_cancel_returned = future.cancel()
        future.result()
        thread_seconds = time.perf_counter() - requested
    process = context.Process(target=blocked_child, args=(f"{base}/stall", str(work)))
    process.start()
    time.sleep(CANCEL_AFTER_SECONDS)
    requested = time.perf_counter()
    process.terminate()
    process.join()
    process_seconds = time.perf_counter() - requested
    return {
        "socket_timeout_seconds": SOCKET_TIMEOUT_SECONDS,
        "thread_cooperative": {
            "seconds_until_the_operation_stopped": round(thread_seconds, 3),
            "progress_hook_calls": hook_calls,
            "future_cancel_returned": future_cancel_returned,
        },
        "process_terminated": {
            "seconds_until_the_operation_stopped": round(process_seconds, 3),
            "exit_code": process.exitcode,
        },
    }


def alive(pid: int) -> bool:
    """El proceso existe y no es un zombi."""
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except FileNotFoundError:
        return False
    return state != "Z"


def descendants_experiment(context: Any) -> dict[str, Any]:
    """Un hijo externo lanzado desde un hilo o desde un líder de grupo."""
    child_pid: list[int] = []

    def thread_job(stop: threading.Event) -> None:
        child = subprocess.Popen(["sleep", "60"])
        child_pid.append(child.pid)
        stop.wait()  # el hilo «se cancela»: deja de esperar, el hijo sigue

    stop = threading.Event()
    thread = threading.Thread(target=thread_job, args=(stop,))
    thread.start()
    while not child_pid:
        time.sleep(0.01)
    stop.set()
    thread.join()
    thread_child_survived = alive(child_pid[0])
    os.kill(child_pid[0], signal.SIGKILL)
    with contextlib.suppress(ChildProcessError):
        os.waitpid(child_pid[0], 0)
    pids = context.Queue()
    leader = context.Process(target=leader_with_external_child, args=(pids,))
    leader.start()
    external = pids.get(timeout=30)
    os.killpg(leader.pid, signal.SIGKILL)
    leader.join()
    deadline = time.monotonic() + 2
    while alive(external) and time.monotonic() < deadline:
        time.sleep(0.01)
    return {
        "thread_cancelled_external_child_survived": thread_child_survived,
        "process_group_terminated_external_child_survived": alive(external),
    }


CRASH_SCRIPT = """
import os, sys, threading, time
done = []
def long_job():
    time.sleep(1.0)
    done.append("other job finished")
other = threading.Thread(target=long_job)
other.start()
time.sleep(0.2)
os.abort()
"""


def crash_isolation_experiment(context: Any) -> dict[str, Any]:
    """Fallo nativo en un hilo frente a fallo nativo en un proceso aparte."""
    threads = subprocess.run(
        [sys.executable, "-c", CRASH_SCRIPT + "\nother.join()\nprint(done)"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    crashing = context.Process(target=os.abort)
    survivor = context.Process(target=time.sleep, args=(1.0,))
    survivor.start()
    crashing.start()
    crashing.join()
    survivor.join()
    return {
        "threads_same_process": {
            "exit_code": threads.returncode,
            "other_job_finished": "other job finished" in threads.stdout,
        },
        "separate_processes": {
            "crashed_exit_code": crashing.exitcode,
            "other_job_exit_code": survivor.exitcode,
        },
    }


def event_loop_experiment(base: str, work: Path) -> dict[str, Any]:
    """Retardo máximo del event loop con yt-dlp dentro o fuera del loop."""

    async def measure(run: Callable[[], Any]) -> float:
        worst = 0.0
        finished = asyncio.Event()

        async def ticker() -> None:
            nonlocal worst
            while not finished.is_set():
                expected = time.perf_counter() + 0.01
                await asyncio.sleep(0.01)
                worst = max(worst, time.perf_counter() - expected)

        tick = asyncio.create_task(ticker())
        await asyncio.sleep(0.05)
        await run()
        finished.set()
        await tick
        return worst

    url = f"{base}/media-loop.mp4"

    async def blocking() -> None:
        download(url, work)

    async def offloaded() -> None:
        await asyncio.to_thread(download, url, work)

    return {
        "download_seconds_expected": round(MEDIA_SIZE / BYTES_PER_SECOND, 3),
        "max_loop_lag_seconds_blocking_call": round(asyncio.run(measure(blocking)), 3),
        "max_loop_lag_seconds_to_thread": round(asyncio.run(measure(offloaded)), 3),
    }


def event_overhead_experiment(context: Any) -> dict[str, Any]:
    """Coste por mensaje entre procesos frente a una llamada local."""
    count = 20_000
    messages = context.Queue()
    sender = context.Process(target=message_sender, args=(messages, count))
    sender.start()
    first = messages.get(timeout=60)
    started = time.perf_counter()
    received = 1 if first is not None else 0
    while messages.get(timeout=60) is not None:
        received += 1
    cross_process = (time.perf_counter() - started) / max(received - 1, 1)
    sender.join()
    collected: list[Any] = []
    started = time.perf_counter()
    for index in range(count):
        collected.append(("progress", index, 1024 * index, None))
    in_process = (time.perf_counter() - started) / count
    return {
        "messages": count,
        "cross_process_microseconds_per_message": round(cross_process * 1e6, 2),
        "in_process_microseconds_per_message": round(in_process * 1e6, 3),
    }


def memory_growth_experiment(base: str, work: Path, context: Any) -> dict[str, Any]:
    """Memoria de un proceso tras descargas sucesivas (un YoutubeDL por job)."""
    jobs = 30
    results = context.Queue()
    child = context.Process(
        target=successive_downloads_child,
        args=(f"{base}/media-memory.mp4", str(work), jobs, results),
    )
    child.start()
    samples = []
    while (sample := results.get(timeout=300)) is not None:
        samples.append(sample)
    child.join()
    return {
        "jobs": jobs,
        "rss_mib_after_job": {
            str(index + 1): round(samples[index] / 1024, 1)
            for index in (0, 4, 9, 19, 29)
            if index < len(samples)
        },
    }


def consumer_without_cli_experiment(base: str, work: Path) -> dict[str, Any]:
    """Ciclo completo con los componentes del producto, sin command_line."""
    from queued_media_downloader.job_queue import (
        CancelJob,
        EnqueueMedia,
        ListJobs,
        RecoverInterruptedJobs,
        RunQueue,
        ShowJob,
    )
    from queued_media_downloader.job_storage.sqlite_connection import (
        open_database,
    )
    from queued_media_downloader.job_storage.sqlite_job_request_inbox import (
        SqliteJobRequestInbox,
    )
    from queued_media_downloader.job_storage.sqlite_job_store import (
        SqliteJobStore,
    )
    from queued_media_downloader.jobs import DownloadOptions
    from queued_media_downloader.media_extraction import (
        MediaSourceSettings,
    )
    from queued_media_downloader.media_extraction.yt_dlp_media_source import (
        YtDlpMediaSource,
    )
    from queued_media_downloader.workers.posix_process_tree_terminator import (
        PosixProcessTreeTerminator,
    )
    from queued_media_downloader.workers.process_worker_pool import (
        ProcessWorkerPool,
    )

    state = work / "installation" / "state"
    state.mkdir(parents=True)
    connection = open_database(state / "queue.sqlite3")
    store, inbox = SqliteJobStore(connection), SqliteJobRequestInbox(connection)
    options = DownloadOptions(
        format_selector="b",
        download_directory=work / "installation" / "downloads",
        output_template="%(title)s [%(id)s].%(ext)s",
        audio_only=False,
    )
    enqueued = EnqueueMedia(store).execute([f"{base}/media-consumer.mp4"], options)
    recovered = RecoverInterruptedJobs(store).execute()
    settings = MediaSourceSettings(
        cache_directory=state / "yt-dlp-cache",
        output_claims_directory=state / "output-claims",
        ffmpeg_location=None,
        max_filename_length=150,
        progress_interval_seconds=0.5,
    )
    observed: list[str] = []
    pool = ProcessWorkerPool(
        1, functools.partial(YtDlpMediaSource, settings), PosixProcessTreeTerminator
    )
    try:
        result = RunQueue(
            store,
            pool,
            inbox,
            present=lambda message, _job: observed.append(
                type(message.job_event).__name__
            ),
        ).execute()
    finally:
        pool.shut_down()
    jobs = ListJobs(store).execute()
    details = ShowJob(store).execute(jobs[-1].job_id)  # type: ignore[arg-type]
    cancel = CancelJob(store, inbox).execute([enqueued[0]])
    connection.close()
    return {
        "imported_command_line": "queued_media_downloader.command_line" in sys.modules,
        "jobs": [(job.kind.name, job.status.name) for job in jobs],
        "output_present": details.job.output_path is not None,
        "failed_job_count": result.failed_job_count,
        "observed_event_types": sorted(set(observed)),
        "recovered": str(recovered),
        "cancel_of_finished_job_already_finished": len(cancel.already_finished),
        "internal_modules_needed": [
            "job_storage.sqlite_connection",
            "job_storage.sqlite_job_store",
            "job_storage.sqlite_job_request_inbox",
            "media_extraction.yt_dlp_media_source",
            "workers.process_worker_pool",
            "workers.posix_process_tree_terminator",
        ],
        "observation_type_received": "WorkerMessage",
    }


def main() -> int:
    """Ejecuta los experimentos y escribe sus resultados."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    context = multiprocessing.get_context("spawn")
    with tempfile.TemporaryDirectory() as temporary, media_server() as base:
        work = Path(temporary)
        results = {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "yt_dlp": yt_dlp.version.__version__,
            "cpu_count": os.cpu_count(),
            "startup": startup_experiment(context),
            "concurrency": concurrency_experiment(base, work / "concurrency", context),
            "blocked_cancellation": blocked_cancellation_experiment(
                base, work, context
            ),
            "descendants": descendants_experiment(context),
            "crash_isolation": crash_isolation_experiment(context),
            "event_loop": event_loop_experiment(base, work / "loop"),
            "event_overhead": event_overhead_experiment(context),
            "memory_growth": memory_growth_experiment(base, work / "memory", context),
            "consumer_without_cli": consumer_without_cli_experiment(
                base, work / "consumer"
            ),
        }
    arguments.output.write_text(json.dumps(results, indent=2) + "\n", "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
