"""Terminación del árbol de un worker con un Job Object de Windows (ADR-0029).

Un Job Object por worker, con JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE:
- Todo proceso que el worker cree después de asignarlo queda dentro, a
  cualquier profundidad: yt-dlp lanza ffmpeg y deno sin
  CREATE_BREAKAWAY_FROM_JOB, y sin JOB_OBJECT_LIMIT_BREAKAWAY_OK ningún proceso
  puede salir.
- TerminateJobObject termina todos los procesos que contiene, también los
  descendientes de un worker que ya murió.
- Si el proceso principal muere, Windows cierra su handle y termina el árbol.
- Opera sobre handles, no sobre PID: no le afecta la reutilización de PID.

El handle del Job Object no es heredable (CreateJobObjectW sin atributos de
seguridad), así que ningún proceso hijo lo recibe ni lo mantiene abierto.

Asociación al crear el proceso: multiprocessing crea el worker sin
CREATE_SUSPENDED ni PROC_THREAD_ATTRIBUTE_JOB_LIST, así que la asignación
ocurre justo después de crearlo. No hay carrera: el worker solo lanza procesos
al ejecutar un job, y el pool no le envía ninguno hasta haberlo registrado.

Validación en Windows: pendiente, en la campaña final (plan de E2, §7).
"""

import sys
import time

from queued_media_downloader.workers.process_tree_terminator import (
    ProcessTreeTerminationError,
)

# Cuánto se espera a que el Job Object quede sin procesos tras terminarlo.
TERMINATION_TIMEOUT_SECONDS = 10.0

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    _kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    _kernel32.QueryInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    _kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    _PROCESS_TERMINATE = 0x0001
    _PROCESS_SET_QUOTA = 0x0100
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
    _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    _TERMINATED_BY_PARENT_EXIT_CODE = 1

    class _IoCounters(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_ulonglong)
            for name in (
                "ReadOperationCount",
                "WriteOperationCount",
                "OtherOperationCount",
                "ReadTransferCount",
                "WriteTransferCount",
                "OtherTransferCount",
            )
        ]

    class _BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BasicLimitInformation),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    class _BasicAccountingInformation(ctypes.Structure):
        _fields_ = [
            ("TotalUserTime", ctypes.c_int64),
            ("TotalKernelTime", ctypes.c_int64),
            ("ThisPeriodTotalUserTime", ctypes.c_int64),
            ("ThisPeriodTotalKernelTime", ctypes.c_int64),
            ("TotalPageFaultCount", wintypes.DWORD),
            ("TotalProcesses", wintypes.DWORD),
            ("ActiveProcesses", wintypes.DWORD),
            ("TotalTerminatedProcesses", wintypes.DWORD),
        ]

    def _last_error(action: str) -> ProcessTreeTerminationError:
        windows_error = ctypes.WinError(ctypes.get_last_error())
        return ProcessTreeTerminationError(f"Could not {action}: {windows_error}")

    class WindowsProcessTreeTerminator:
        """Un Job Object con KILL_ON_JOB_CLOSE para el árbol de un worker."""

        def __init__(self) -> None:
            """Crea el Job Object y le pone JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE.

            Raises:
                ProcessTreeTerminationError: Si Windows no lo permite.
            """
            job_handle = _kernel32.CreateJobObjectW(None, None)
            if not job_handle:
                raise _last_error("create the job object of a worker")
            self._job_handle: int | None = job_handle
            limits = _ExtendedLimitInformation()
            limits.BasicLimitInformation.LimitFlags = (
                _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            )
            if not _kernel32.SetInformationJobObject(
                job_handle,
                _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(limits),
                ctypes.sizeof(limits),
            ):
                error = _last_error("configure the job object of a worker")
                self.release()
                raise error

        def register_root_process(self, process_id: int) -> None:
            """Asigna el worker al Job Object.

            multiprocessing mantiene abierto un handle del worker, así que su
            PID no puede reutilizarse entre su creación y esta llamada.
            """
            if self._job_handle is None:
                message = "The terminator was already released"
                raise ProcessTreeTerminationError(message)
            process_handle = _kernel32.OpenProcess(
                _PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, process_id
            )
            if not process_handle:
                raise _last_error(f"open worker process {process_id}")
            try:
                if not _kernel32.AssignProcessToJobObject(
                    self._job_handle, process_handle
                ):
                    raise _last_error(f"assign worker process {process_id}")
            finally:
                _kernel32.CloseHandle(process_handle)

        def terminate_tree(self) -> None:
            """Termina todos los procesos del Job Object y espera a que acaben.

            Raises:
                ProcessTreeTerminationError: Si quedan procesos tras el plazo.
            """
            if self._job_handle is None:
                return
            if not _kernel32.TerminateJobObject(
                self._job_handle, _TERMINATED_BY_PARENT_EXIT_CODE
            ):
                raise _last_error("terminate the processes of a worker")
            deadline = time.monotonic() + TERMINATION_TIMEOUT_SECONDS
            while self._active_process_count() > 0:
                if time.monotonic() >= deadline:
                    message = "Processes of a worker are still running"
                    raise ProcessTreeTerminationError(message)
                time.sleep(0.05)

        def release(self) -> None:
            """Cierra el handle: Windows termina lo que quede en el Job Object."""
            if self._job_handle is not None:
                _kernel32.CloseHandle(self._job_handle)
                self._job_handle = None

        def _active_process_count(self) -> int:
            accounting = _BasicAccountingInformation()
            if not _kernel32.QueryInformationJobObject(
                self._job_handle,
                _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
                ctypes.byref(accounting),
                ctypes.sizeof(accounting),
                None,
            ):
                raise _last_error("query the processes of a worker")
            return int(accounting.ActiveProcesses)
