"""El worker no atiende Ctrl+C: solo el proceso principal decide (UC-05 A6).

Ctrl+C llega a todos los procesos de la consola. En Windows, worker, ffmpeg y
deno comparten la consola y su grupo de procesos (ADR-0029, hallazgo 4); sin
esto, el worker moriría con KeyboardInterrupt en mitad de yt-dlp y ffmpeg
abandonaría la unión. El proceso principal detiene los jobs por su cuenta.
"""

import signal
import sys


def ignore_console_interrupts() -> None:
    """Ignora Ctrl+C en el proceso actual y en los que lance después.

    En Windows, SetConsoleCtrlHandler(NULL, TRUE) hace que el proceso ignore
    CTRL_C_EVENT, y los procesos hijos heredan ese atributo. En POSIX, un
    SIGINT ignorado se mantiene ignorado tras exec en los hijos.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if sys.platform == "win32":
        import ctypes

        ctypes.WinDLL("kernel32").SetConsoleCtrlHandler(None, True)
