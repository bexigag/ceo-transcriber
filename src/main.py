import sys

from src.config import load_config
from src.youtube import (
    parse_youtube_url,
    get_transcript,
    get_playlist_video_ids,
    get_video_metadata,
)
from src.whisper_fallback import transcribe_with_whisper
from src.analyzer import analyze_transcript
from src.notion_db import create_database, add_row


def process_video(video_id: str, database_id: str, config: dict) -> str:
    print(f"  Fetching metadata for {video_id}...")
    metadata = get_video_metadata(video_id)

    print(f"  Title: {metadata['title']}")
    print(f"  Fetching transcript...")

    transcript = get_transcript(video_id)
    if transcript is None:
        print(f"  No captions found. Trying Whisper fallback...")
        transcript = transcribe_with_whisper(video_id)

    if transcript is None:
        print(f"  ERROR: Could not get transcript for {video_id}")
        return add_row(
            token=config["notion_token"],
            database_id=database_id,
            video_url=metadata["url"],
            analysis=None,
            status="Erro",
        )

    print(f"  Transcript: {len(transcript)} characters. Analyzing with Gemini...")

    analysis = analyze_transcript(
        transcript=transcript,
        metadata=metadata,
        api_key=config["gemini_api_key"],
    )

    if analysis is None:
        print(f"  ERROR: Gemini analysis failed for {video_id}")
        return add_row(
            token=config["notion_token"],
            database_id=database_id,
            video_url=metadata["url"],
            analysis=None,
            status="Erro",
        )

    print(f"  Analysis complete. Writing to Notion...")

    return add_row(
        token=config["notion_token"],
        database_id=database_id,
        video_url=metadata["url"],
        analysis=analysis,
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <youtube-url> [--db-id <notion-database-id>]")
        sys.exit(1)

    url = sys.argv[1]
    config = load_config()

    # Check for existing database ID or create new one
    db_id = None
    if "--db-id" in sys.argv:
        db_id = sys.argv[sys.argv.index("--db-id") + 1]
    else:
        print("No --db-id provided. Creating new Notion database...")
        db_id = create_database(
            token=config["notion_token"],
            parent_page_id=config["notion_parent_page_id"],
        )
        print(f"Created database: {db_id}")
        print(f"Re-run with: --db-id {db_id}")

    parsed = parse_youtube_url(url)

    if parsed["type"] == "video":
        print(f"\nProcessing single video: {parsed['video_id']}")
        page_id = process_video(parsed["video_id"], db_id, config)
        print(f"Done! Notion page: {page_id}")

    elif parsed["type"] == "playlist":
        print(f"\nFetching playlist: {parsed['playlist_id']}")
        videos = get_playlist_video_ids(parsed["playlist_id"])
        print(f"Found {len(videos)} videos\n")

        for i, video in enumerate(videos, 1):
            print(f"[{i}/{len(videos)}] Processing: {video['title']}")
            try:
                page_id = process_video(video["id"], db_id, config)
                print(f"  Notion page: {page_id}\n")
            except Exception as e:
                print(f"  ERROR: {e}\n")

    print("All done!")


if __name__ == "__main__":
    main()
