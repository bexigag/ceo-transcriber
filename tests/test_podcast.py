from unittest.mock import patch, MagicMock
from src.podcast import get_ceo_episodes, get_episode_metadata


def test_get_ceo_episodes_returns_list():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "resultCount": 3,
        "results": [
            {"wrapperType": "collection", "collectionName": "O CEO e o limite"},
            {
                "wrapperType": "podcastEpisode",
                "trackName": "Carlos Ribeiro, CEO da Takeda",
                "episodeUrl": "https://traffic.omny.fm/audio1.mp3",
                "releaseDate": "2026-03-02T06:05:00Z",
                "trackViewUrl": "https://podcasts.apple.com/episode1",
            },
            {
                "wrapperType": "podcastEpisode",
                "trackName": "Filipa Pinto Coelho",
                "episodeUrl": "https://traffic.omny.fm/audio2.mp3",
                "releaseDate": "2026-02-23T06:05:00Z",
                "trackViewUrl": "https://podcasts.apple.com/episode2",
            },
        ],
    }

    with patch("src.podcast.requests.get", return_value=mock_resp):
        episodes = get_ceo_episodes()

    assert len(episodes) == 2
    assert episodes[0]["title"] == "Carlos Ribeiro, CEO da Takeda"
    assert episodes[0]["audio_url"] == "https://traffic.omny.fm/audio1.mp3"


def test_get_ceo_episodes_skips_collection_entry():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "resultCount": 2,
        "results": [
            {"wrapperType": "collection", "collectionName": "O CEO e o limite"},
            {
                "wrapperType": "podcastEpisode",
                "trackName": "Episode 1",
                "episodeUrl": "https://example.com/ep1.mp3",
                "releaseDate": "2026-01-01T00:00:00Z",
                "trackViewUrl": "https://example.com/ep1",
            },
        ],
    }

    with patch("src.podcast.requests.get", return_value=mock_resp):
        episodes = get_ceo_episodes()

    assert len(episodes) == 1


def test_get_episode_metadata():
    episode = {
        "title": "Carlos Ribeiro, CEO da Takeda",
        "audio_url": "https://traffic.omny.fm/audio1.mp3",
        "published": "2026-03-02T06:05:00Z",
        "link": "https://podcasts.apple.com/episode1",
    }
    metadata = get_episode_metadata(episode)
    assert metadata["title"] == "Carlos Ribeiro, CEO da Takeda"
    assert metadata["url"] == "https://podcasts.apple.com/episode1"


def test_get_transcript_supadata_file_success():
    from streamlit_app import get_transcript_supadata_file

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"content": "transcribed text here", "lang": "pt"}

    with patch("streamlit_app.requests.get", return_value=mock_resp):
        result = get_transcript_supadata_file("https://example.com/ep.mp3", "fake-key")
        assert result == "transcribed text here"


def test_get_transcript_supadata_file_async_job():
    from streamlit_app import get_transcript_supadata_file

    mock_resp_202 = MagicMock()
    mock_resp_202.status_code = 202
    mock_resp_202.json.return_value = {"jobId": "job123"}

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {"content": "async result", "lang": "pt"}

    with patch("streamlit_app.requests.get", side_effect=[mock_resp_202, mock_resp_200]):
        with patch("streamlit_app.time.sleep"):
            result = get_transcript_supadata_file("https://example.com/ep.mp3", "fake-key")
            assert result == "async result"


def test_get_transcript_supadata_file_empty_returns_none():
    from streamlit_app import get_transcript_supadata_file

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"content": "   ", "lang": "pt"}

    with patch("streamlit_app.requests.get", return_value=mock_resp):
        result = get_transcript_supadata_file("https://example.com/ep.mp3", "fake-key")
        assert result is None
