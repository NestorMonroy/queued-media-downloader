import re

from queued_media_downloader.media_extraction.yt_dlp_javascript_runtime import (
    find_deno,
)


def test_finds_the_deno_installed_with_the_project() -> None:
    deno = find_deno()

    assert deno is not None
    assert deno.name == "deno"
    assert re.fullmatch(r"\d+\.\d+\.\d+", deno.version)
    assert deno.minimum_version == "2.3.0"
    assert deno.is_supported
    assert deno.path.is_file()
