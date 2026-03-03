import os
from unittest.mock import patch, MagicMock
from src.whisper_fallback import transcribe_with_whisper


def test_transcribe_with_whisper_downloads_and_transcribes():
    with patch("src.whisper_fallback.YoutubeDL") as mock_ydl_class, \
         patch("src.whisper_fallback.whisper") as mock_whisper:

        mock_ydl = MagicMock()
        mock_ydl.prepare_filename.return_value = "/tmp/video.webm"
        mock_ydl.extract_info.return_value = {"title": "test"}
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_class.return_value = mock_ydl

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "Hello from Whisper"}
        mock_whisper.load_model.return_value = mock_model

        with patch("os.path.exists", return_value=True), \
             patch("os.remove"):
            result = transcribe_with_whisper("fake_video_id")

    assert result == "Hello from Whisper"


def test_transcribe_with_whisper_returns_none_on_error():
    with patch("src.whisper_fallback.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = Exception("Download failed")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl_class.return_value = mock_ydl

        result = transcribe_with_whisper("fake_video_id")

    assert result is None
