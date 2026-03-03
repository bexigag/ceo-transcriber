import os
import pytest
from src.config import load_config


def test_load_config_returns_all_keys(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("NOTION_TOKEN", "test-token")
    monkeypatch.setenv("NOTION_PARENT_PAGE_ID", "test-page-id")

    config = load_config()

    assert config["gemini_api_key"] == "test-key"
    assert config["notion_token"] == "test-token"
    assert config["notion_parent_page_id"] == "test-page-id"


def test_load_config_raises_on_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_PARENT_PAGE_ID", raising=False)

    with pytest.raises(ValueError, match="Missing required"):
        load_config()
