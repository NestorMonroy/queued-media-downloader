"""Versiones instaladas de yt-dlp y de su solucionador de retos (yt-dlp-ejs).

Se leen de los metadatos de los paquetes, sin importar yt_dlp, para que
diagnose y la evidencia de las validaciones digan con qué versión se trabajó
(ADR-0002, SUP-S01).
"""

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version


@dataclass(frozen=True, slots=True)
class YtDlpVersions:
    """yt-dlp y yt-dlp-ejs; challenge_solver es None si no está instalado."""

    yt_dlp: str
    challenge_solver: str | None


def installed_yt_dlp_versions() -> YtDlpVersions:
    """Versiones del entorno virtual del proyecto."""
    try:
        challenge_solver: str | None = version("yt-dlp-ejs")
    except PackageNotFoundError:
        challenge_solver = None
    return YtDlpVersions(yt_dlp=version("yt-dlp"), challenge_solver=challenge_solver)
