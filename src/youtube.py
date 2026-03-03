import re
from urllib.parse import urlparse, parse_qs


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)

    if parsed.hostname in ("youtu.be",):
        return parsed.path.lstrip("/")

    if parsed.hostname in ("www.youtube.com", "youtube.com"):
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]

    raise ValueError(f"Cannot extract video ID from: {url}")


def parse_youtube_url(url: str) -> dict:
    parsed = urlparse(url)

    if parsed.hostname not in ("www.youtube.com", "youtube.com", "youtu.be"):
        raise ValueError(f"Invalid YouTube URL: {url}")

    qs = parse_qs(parsed.query)

    if "list" in qs and parsed.path == "/playlist":
        return {"type": "playlist", "playlist_id": qs["list"][0]}

    video_id = extract_video_id(url)
    return {"type": "video", "video_id": video_id}
