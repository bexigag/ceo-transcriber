import os
from dotenv import load_dotenv


def load_config() -> dict:
    load_dotenv()

    required_keys = [
        "GEMINI_API_KEY",
        "NOTION_TOKEN",
        "NOTION_PARENT_PAGE_ID",
    ]

    missing = [k for k in required_keys if not os.getenv(k)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return {
        "gemini_api_key": os.getenv("GEMINI_API_KEY"),
        "notion_token": os.getenv("NOTION_TOKEN"),
        "notion_parent_page_id": os.getenv("NOTION_PARENT_PAGE_ID"),
    }
