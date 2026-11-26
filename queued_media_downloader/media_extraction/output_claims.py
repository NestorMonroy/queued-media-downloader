"""Propiedad de los archivos finales: ningún job toca el archivo de otro.

Riesgo R-14 (auditoría, §7). Con una plantilla sin %(id)s o un título
recortado, dos contenidos pueden recibir el mismo nombre final. yt-dlp toma
entonces el archivo existente por "ya descargado", pero aun así le aplica
fixup y los postprocessors (YoutubeDL.process_info, versión fijada
2026.10.26), y FFmpegExtractAudio lo sobrescribe. Detectar la colisión
después, con el índice unique_output_path, llega tarde.

Por eso cada job reclama su nombre final antes de descargar (postprocessor
before_dl, OutputOwnershipGuard). La reclamación es un archivo creado de forma
exclusiva (O_CREAT | O_EXCL, atómico en NTFS y en sistemas POSIX locales) en
la carpeta de reclamaciones del estado, con el id del job dentro. Se reclama
la ruta sin extensión (carpeta final + nombre base): la extensión final puede
cambiar al unir formatos o extraer el audio.

- Si otro job tiene la reclamación, el job falla sin tocar nada.
- Si la reclamación es nueva y ya hay un archivo con ese nombre base, el
  archivo es de otro (un job purgado, una versión anterior o el usuario): el
  job falla y suelta la reclamación.
- Si la reclamación ya era de este job, el archivo existente es suyo (un
  cierre después de moverlo y antes de registrar JobCompleted).

La reclamación se conserva mientras el job es dueño del archivo y se suelta
al fallar o cancelar sin archivo final, o al purgar el job (UC-10).
"""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

CLAIM_SUFFIX = ".claim"


class OutputClaimedError(OSError):
    """El nombre final del job es de otro job o de un archivo que no es suyo."""


@dataclass(frozen=True, slots=True)
class OutputClaim:
    """Reclamación de un nombre final: su archivo y el nombre que protege."""

    claim_path: Path
    final_directory: Path
    stem: str


def canonical_stem_path(final_path: Path) -> str:
    """Ruta sin extensión con la que se comparan dos nombres finales.

    realpath resuelve enlaces y rutas relativas; normcase hace que en Windows
    "C:/A/Video" y su versión en minúsculas con barras invertidas sean la
    misma ruta, como para NTFS (sin distinguir mayúsculas). No se normaliza
    Unicode: NTFS tampoco lo hace.
    """
    directory = os.path.realpath(final_path.parent)
    return os.path.normcase(os.path.join(directory, final_path.stem))


def existing_files_with_stem(final_directory: Path, stem: str) -> list[Path]:
    """Archivos de la carpeta final con ese nombre base y cualquier extensión."""
    if not final_directory.is_dir():
        return []
    wanted = os.path.normcase(stem)
    return sorted(
        Path(entry.path)
        for entry in os.scandir(final_directory)
        if entry.is_file()
        and os.path.normcase(os.path.splitext(entry.name)[0]) == wanted
    )


class OutputClaims:
    """Reclamaciones de nombres finales, una por archivo en claims_directory."""

    def __init__(self, claims_directory: Path) -> None:
        """Guarda las reclamaciones en claims_directory (dentro del estado)."""
        self._claims_directory = claims_directory

    def claim(self, job_id: int, final_path: Path) -> OutputClaim:
        """Reclama para job_id el nombre final de final_path.

        Raises:
            OutputClaimedError: Si el nombre es de otro job o ya hay un archivo
                con ese nombre base que no es de job_id.
        """
        stem_path = canonical_stem_path(final_path)
        digest = hashlib.sha256(stem_path.encode("utf-8")).hexdigest()
        claim = OutputClaim(
            claim_path=self._claims_directory / f"{digest}{CLAIM_SUFFIX}",
            final_directory=final_path.parent,
            stem=final_path.stem,
        )
        self._claims_directory.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(
                claim.claim_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644
            )
        except FileExistsError:
            owner = self._owner_of(claim.claim_path)
            if owner != job_id:
                message = (
                    f"{final_path.with_suffix('')}.* belongs to job {owner}; "
                    "use an output template that keeps %(id)s"
                )
                raise OutputClaimedError(message) from None
            return claim
        with os.fdopen(descriptor, "w", encoding="utf-8") as claim_file:
            claim_file.write(f"{job_id}\n{stem_path}\n")
        existing = existing_files_with_stem(claim.final_directory, claim.stem)
        if existing:
            self.release(claim)
            message = (
                f"{existing[0]} already exists and was not written by this job; "
                "move it or use an output template that keeps %(id)s"
            )
            raise OutputClaimedError(message)
        return claim

    def release(self, claim: OutputClaim) -> None:
        """Suelta la reclamación; si ya no existe, no hace nada."""
        claim.claim_path.unlink(missing_ok=True)

    def release_unless_file_kept(self, claim: OutputClaim) -> None:
        """Suelta la reclamación de un job que falló, salvo que dejara su archivo."""
        if not existing_files_with_stem(claim.final_directory, claim.stem):
            self.release(claim)

    def release_all_of(self, job_id: int) -> None:
        """Suelta todas las reclamaciones de un job que se borra de la cola."""
        if not self._claims_directory.is_dir():
            return
        for claim_path in self._claims_directory.glob(f"*{CLAIM_SUFFIX}"):
            if self._owner_of(claim_path) == job_id:
                claim_path.unlink(missing_ok=True)

    @staticmethod
    def _owner_of(claim_path: Path) -> int | str:
        """Id del job dueño; el texto leído si no es un id (archivo dañado)."""
        try:
            first_line = claim_path.read_text(encoding="utf-8").partition("\n")[0]
        except OSError:
            return "unknown"
        return int(first_line) if first_line.isdigit() else repr(first_line)
