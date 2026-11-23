"""Runtime de JavaScript que yt-dlp usa para algunos sitios, como YouTube."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class JavaScriptRuntime:
    """Runtime encontrado por yt-dlp; is_supported compara con minimum_version."""

    name: str
    path: Path
    version: str
    minimum_version: str
    is_supported: bool
