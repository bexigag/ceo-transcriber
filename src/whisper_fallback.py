import os
import tempfile
import importlib
from yt_dlp import YoutubeDL

# Lazy import — whisper is an optional dependency
whisper = None


def _ensure_whisper():
    global whisper
    if whisper is None:
        whisper = importlib.import_module("whisper")


def transcribe_with_whisper(video_id: str, model_size: str = "base") -> str | None:
    tmp_dir = tempfile.mkdtemp()
    audio_path = None

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "outtmpl": os.path.join(tmp_dir, "%(id)s.%(ext)s"),
            "quiet": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}",
                download=True,
            )
            audio_path = os.path.join(tmp_dir, f"{video_id}.mp3")

        _ensure_whisper()
        model = whisper.load_model(model_size)
        result = model.transcribe(audio_path)
        return result["text"]

    except Exception:
        return None

    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
