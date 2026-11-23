"""Plantilla de salida de los jobs hijos de una playlist (ADR-0028).

Sigue el ejemplo de yt-dlp "%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s"
con el contexto guardado en el job, sin volver a extraer la playlist y sin
extra_info (ADR-0009).
"""

from yt_dlp.utils import sanitize_filename

from queued_media_downloader.jobs import PlaylistContext


def build_playlist_output_template(
    output_template: str, playlist_context: PlaylistContext, max_filename_length: int
) -> str:
    """Antepone a output_template la carpeta de la playlist y el índice.

    La carpeta es el título de la playlist o, sin título, su id, saneado como
    sanea yt-dlp el campo playlist y recortado a max_filename_length. El índice
    se rellena con ceros hasta las cifras del número de entradas; si no se
    conoce, no se rellena, como hace yt-dlp con lazy_playlist.
    """
    folder_name = _folder_name_of(playlist_context, max_filename_length)
    index_width = len(str(playlist_context.playlist_entry_count or ""))
    playlist_index = f"{playlist_context.playlist_index:0{index_width}d}"
    return f"{_escape_percent(folder_name)}/{playlist_index} - {output_template}"


def _folder_name_of(playlist_context: PlaylistContext, max_filename_length: int) -> str:
    """Nombre de la carpeta de la playlist, válido como nombre de archivo."""
    playlist_name = playlist_context.playlist_title or playlist_context.playlist_id
    folder_name = sanitize_filename(playlist_name)[:max_filename_length]
    # Recortar puede dejar un espacio al final, que Windows no admite.
    return folder_name.rstrip() or "_"


def _escape_percent(text: str) -> str:
    """Evita que yt-dlp lea un % del texto como el inicio de un campo."""
    return text.replace("%", "%%")
