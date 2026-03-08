import requests

ITUNES_PODCAST_ID = "1662139036"


def get_ceo_episodes() -> list[dict]:
    """Fetch all episodes of 'O CEO e o Limite' from iTunes Lookup API."""
    resp = requests.get(
        "https://itunes.apple.com/lookup",
        params={
            "id": ITUNES_PODCAST_ID,
            "media": "podcast",
            "entity": "podcastEpisode",
            "limit": 300,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    episodes = []
    for item in data.get("results", []):
        if item.get("wrapperType") != "podcastEpisode":
            continue
        audio_url = item.get("episodeUrl")
        if not audio_url:
            continue
        episodes.append({
            "title": item.get("trackName", "Sem titulo"),
            "audio_url": audio_url,
            "published": item.get("releaseDate", ""),
            "link": item.get("trackViewUrl", ""),
        })

    return episodes


def get_episode_metadata(episode: dict) -> dict:
    """Format episode data for the analyzer module."""
    return {
        "title": episode.get("title", "Sem titulo"),
        "description": "",
        "uploader": "O CEO e o Limite",
        "upload_date": episode.get("published", ""),
        "url": episode.get("link", episode.get("audio_url", "")),
    }
