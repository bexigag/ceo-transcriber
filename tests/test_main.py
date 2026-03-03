import sys
from unittest.mock import patch, MagicMock
from src.main import process_video, main


def test_process_video_full_pipeline():
    mock_config = {
        "anthropic_api_key": "test-key",
        "notion_token": "test-token",
        "notion_parent_page_id": "page-id",
    }

    with patch("src.main.get_video_metadata") as mock_meta, \
         patch("src.main.get_transcript") as mock_transcript, \
         patch("src.main.analyze_transcript") as mock_analyze, \
         patch("src.main.add_row") as mock_add_row:

        mock_meta.return_value = {
            "title": "CEO Interview",
            "description": "About AI",
            "url": "https://youtube.com/watch?v=abc",
        }
        mock_transcript.return_value = "CEO talks about AI strategy"
        mock_analyze.return_value = {"nome": "John", "cargo": "CEO"}
        mock_add_row.return_value = "page-123"

        result = process_video("abc", "db-id", mock_config)

    assert result == "page-123"
    mock_transcript.assert_called_once_with("abc")
    mock_analyze.assert_called_once()


def test_process_video_uses_whisper_fallback():
    mock_config = {
        "anthropic_api_key": "test-key",
        "notion_token": "test-token",
        "notion_parent_page_id": "page-id",
    }

    with patch("src.main.get_video_metadata") as mock_meta, \
         patch("src.main.get_transcript", return_value=None), \
         patch("src.main.transcribe_with_whisper") as mock_whisper, \
         patch("src.main.analyze_transcript") as mock_analyze, \
         patch("src.main.add_row") as mock_add_row:

        mock_meta.return_value = {"title": "T", "description": "D", "url": "http://y.com"}
        mock_whisper.return_value = "Whisper transcription"
        mock_analyze.return_value = {"nome": "Jane"}
        mock_add_row.return_value = "page-456"

        result = process_video("abc", "db-id", mock_config)

    assert result == "page-456"
    mock_whisper.assert_called_once_with("abc")
