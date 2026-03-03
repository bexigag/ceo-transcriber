import pytest
from src.youtube import parse_youtube_url, extract_video_id


def test_extract_video_id_standard_url():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_short_url():
    url = "https://youtu.be/dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_with_extra_params():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_parse_youtube_url_single_video():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    result = parse_youtube_url(url)
    assert result["type"] == "video"
    assert result["video_id"] == "dQw4w9WgXcQ"


def test_parse_youtube_url_playlist():
    url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
    result = parse_youtube_url(url)
    assert result["type"] == "playlist"
    assert result["playlist_id"] == "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"


def test_parse_youtube_url_invalid():
    with pytest.raises(ValueError, match="Invalid YouTube URL"):
        parse_youtube_url("https://example.com/not-youtube")
