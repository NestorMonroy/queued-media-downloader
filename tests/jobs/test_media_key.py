import pytest

from queued_media_downloader.jobs import MediaKey


@pytest.mark.parametrize(
    ("extractor_key", "media_id"),
    [("", "abc123"), ("Youtube", ""), ("   ", "abc123")],
    ids=["empty extractor key", "empty media id", "blank extractor key"],
)
def test_media_key_rejects_empty_parts(extractor_key: str, media_id: str) -> None:
    with pytest.raises(ValueError, match="MediaKey"):
        MediaKey(extractor_key=extractor_key, media_id=media_id)


def test_media_keys_with_the_same_parts_identify_the_same_media() -> None:
    first_key = MediaKey(extractor_key="Youtube", media_id="abc123")
    second_key = MediaKey(extractor_key="Youtube", media_id="abc123")

    assert first_key == second_key
    assert hash(first_key) == hash(second_key)
