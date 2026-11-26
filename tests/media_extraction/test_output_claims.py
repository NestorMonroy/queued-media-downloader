import os
import sys
import unicodedata
from pathlib import Path

import pytest

from queued_media_downloader.media_extraction.output_claims import (
    OutputClaimedError,
    OutputClaims,
    canonical_stem_path,
)


@pytest.fixture
def claims(tmp_path: Path) -> OutputClaims:
    return OutputClaims(tmp_path / "state" / "output-claims")


def token(job_id: int) -> str:
    """Owner token de un job guardado (Job.owner_token)."""
    return f"{job_id}@2026-11-26T00:00:00.{job_id:06d}+00:00"


def claim_files(tmp_path: Path) -> list[Path]:
    return sorted((tmp_path / "state" / "output-claims").glob("*.claim"))


def test_a_name_claimed_by_one_job_is_refused_to_another(
    claims: OutputClaims, tmp_path: Path
) -> None:
    final_path = tmp_path / "downloads" / "video.mp4"
    claims.claim(token(1), final_path)

    with pytest.raises(OutputClaimedError, match="belongs to job 1"):
        claims.claim(token(2), final_path)


def test_the_extension_does_not_matter_two_jobs_cannot_share_a_name(
    claims: OutputClaims, tmp_path: Path
) -> None:
    # La extensión final cambia al unir formatos o extraer el audio.
    claims.claim(token(1), tmp_path / "downloads" / "video.webm")

    with pytest.raises(OutputClaimedError):
        claims.claim(token(2), tmp_path / "downloads" / "video.mp4")


def test_the_same_job_can_claim_its_name_again_and_keep_its_file(
    claims: OutputClaims, tmp_path: Path
) -> None:
    # Cierre después de mover el archivo y antes de registrar JobCompleted.
    final_path = tmp_path / "downloads" / "video.mp4"
    claims.claim(token(1), final_path)
    final_path.parent.mkdir()
    final_path.write_bytes(b"finished by job 1")

    claim = claims.claim(token(1), final_path)

    assert claim.claim_path.exists()


def test_a_file_that_is_not_the_jobs_own_is_refused_and_not_claimed(
    claims: OutputClaims, tmp_path: Path
) -> None:
    final_path = tmp_path / "downloads" / "video.mp4"
    final_path.parent.mkdir()
    final_path.write_bytes(b"user file")

    with pytest.raises(OutputClaimedError, match="already exists"):
        claims.claim(token(1), final_path)

    assert claim_files(tmp_path) == []
    assert final_path.read_bytes() == b"user file"


def test_an_existing_file_with_another_extension_is_also_refused(
    claims: OutputClaims, tmp_path: Path
) -> None:
    existing = tmp_path / "downloads" / "video.mkv"
    existing.parent.mkdir()
    existing.write_bytes(b"merged by an earlier version")

    with pytest.raises(OutputClaimedError):
        claims.claim(token(1), tmp_path / "downloads" / "video.mp4")


def test_format_parts_and_longer_names_are_not_the_same_name(
    claims: OutputClaims, tmp_path: Path
) -> None:
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    (downloads / "video.f137.mp4").write_bytes(b"part")
    (downloads / "video 2.mp4").write_bytes(b"other")

    claim = claims.claim(token(1), downloads / "video.mp4")

    assert claim.claim_path.exists()


def test_a_failed_job_without_its_file_releases_its_name(
    claims: OutputClaims, tmp_path: Path
) -> None:
    final_path = tmp_path / "downloads" / "video.mp4"
    claim = claims.claim(token(1), final_path)

    claims.release_unless_file_kept(claim)

    assert claims.claim(token(2), final_path).claim_path.exists()


def test_a_failed_job_that_left_its_file_keeps_its_name(
    claims: OutputClaims, tmp_path: Path
) -> None:
    final_path = tmp_path / "downloads" / "video.mp4"
    claim = claims.claim(token(1), final_path)
    final_path.parent.mkdir()
    final_path.write_bytes(b"moved, then the job failed")

    claims.release_unless_file_kept(claim)

    with pytest.raises(OutputClaimedError, match="belongs to job 1"):
        claims.claim(token(2), final_path)


def test_releasing_all_claims_of_a_purged_job_keeps_the_others(
    claims: OutputClaims, tmp_path: Path
) -> None:
    claims.claim(token(1), tmp_path / "downloads" / "a.mp4")
    claims.claim(token(1), tmp_path / "downloads" / "b.mp4")
    kept = claims.claim(token(12), tmp_path / "downloads" / "c.mp4")

    claims.release_all_of(token(1))

    assert claim_files(tmp_path) == [kept.claim_path]


def test_relative_and_absolute_paths_to_the_same_file_are_one_name(
    claims: OutputClaims, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    claims.claim(token(1), tmp_path / "downloads" / "video.mp4")

    with pytest.raises(OutputClaimedError):
        claims.claim(token(2), Path("downloads") / ".." / "downloads" / "video.mp4")


def test_a_job_with_a_reused_id_never_takes_the_claim_of_the_lost_job(
    claims: OutputClaims, tmp_path: Path
) -> None:
    # Copia antigua de la base de datos restaurada: el id 1 vuelve a usarse.
    final_path = tmp_path / "downloads" / "video.mp4"
    claims.claim("1@2026-01-01T00:00:00+00:00", final_path)

    with pytest.raises(OutputClaimedError, match="restored from an older copy"):
        claims.claim("1@2026-11-26T00:00:00+00:00", final_path)


def test_purge_releases_the_claims_of_a_lost_job_whose_id_was_reused(
    claims: OutputClaims, tmp_path: Path
) -> None:
    claims.claim("1@2026-01-01T00:00:00+00:00", tmp_path / "downloads" / "a.mp4")
    kept = claims.claim(token(1), tmp_path / "downloads" / "b.mp4")

    claims.release_all_except({token(1)})

    assert claim_files(tmp_path) == [kept.claim_path]


def test_a_damaged_claim_file_is_never_taken_as_the_jobs_own(
    claims: OutputClaims, tmp_path: Path
) -> None:
    final_path = tmp_path / "downloads" / "video.mp4"
    claim = claims.claim(token(1), final_path)
    claim.claim_path.write_text("", encoding="utf-8")

    with pytest.raises(OutputClaimedError, match="damaged claim file"):
        claims.claim(token(1), final_path)


def test_names_that_differ_only_in_unicode_normalisation_are_different(
    claims: OutputClaims, tmp_path: Path
) -> None:
    # NTFS y ext4 guardan los nombres tal cual: son dos archivos distintos.
    composed = unicodedata.normalize("NFC", "canción")
    decomposed = unicodedata.normalize("NFD", "canción")
    claims.claim(token(1), tmp_path / "downloads" / f"{composed}.mp4")

    assert claims.claim(token(2), tmp_path / "downloads" / f"{decomposed}.mp4")


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX names keep their case")
def test_on_posix_names_that_differ_in_case_are_different_files(
    claims: OutputClaims, tmp_path: Path
) -> None:
    claims.claim(token(1), tmp_path / "downloads" / "Video.mp4")

    assert claims.claim(token(2), tmp_path / "downloads" / "video.mp4")


@pytest.mark.windows
def test_on_windows_case_and_separators_do_not_make_another_name(
    claims: OutputClaims, tmp_path: Path
) -> None:
    claims.claim(token(1), tmp_path / "Downloads" / "Video.mp4")
    lower_with_slashes = Path(str(tmp_path / "downloads" / "video.mp4").lower())

    assert canonical_stem_path(tmp_path / "Downloads" / "Video.mp4") == (
        canonical_stem_path(Path(str(lower_with_slashes).replace("\\", "/")))
    )
    with pytest.raises(OutputClaimedError):
        claims.claim(token(2), lower_with_slashes)


@pytest.mark.windows
def test_on_windows_an_existing_file_is_found_whatever_its_case(
    claims: OutputClaims, tmp_path: Path
) -> None:
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    (downloads / "VIDEO.MP4").write_bytes(b"other job")

    with pytest.raises(OutputClaimedError, match="already exists"):
        claims.claim(token(1), downloads / "video.mp4")


@pytest.mark.windows
def test_on_windows_a_long_path_is_claimed_and_an_open_file_still_detected(
    claims: OutputClaims, tmp_path: Path
) -> None:
    # Más de 260 caracteres (MAX_PATH): la reclamación usa un hash de longitud
    # fija, y la carpeta final se recorre con el prefijo \\?\ si hace falta.
    deep = tmp_path / ("d" * 120) / ("e" * 120)
    os.makedirs("\\\\?\\" + str(deep))
    long_name = "n" * 60
    existing = Path("\\\\?\\" + str(deep / f"{long_name}.mp4"))
    existing.write_bytes(b"other job")
    with existing.open("rb"):
        with pytest.raises(OutputClaimedError, match="already exists"):
            claims.claim(token(1), Path("\\\\?\\" + str(deep / f"{long_name}.webm")))
        assert claims.claim(token(2), Path("\\\\?\\" + str(deep / "free.mp4")))
