# Spotify Support + Range Selector - Design Document

**Date:** 2026-03-06
**Status:** Approved

## Problem

The current app only supports YouTube as a source for CEO interviews. Many podcasts live on Spotify and the user wants to process them without manually handling one episode at a time. Additionally, large playlists/shows need a range selector to pick which episodes to process.

## Solution

Add Spotify as the default source platform alongside YouTube. Use RSS feeds to list episodes and Supadata to transcribe audio files by URL. Add a two-dropdown range selector for both platforms.

## Architecture

```
Streamlit UI
  |
  v
Platform selector: [Spotify | YouTube]
  |                        |
  v                        v
Spotify show URL       YouTube playlist URL
  |                        |
  v                        v
RSS feed parser        yt-dlp (existing)
  |                        |
  v                        v
Episode list with range selector (De / Ate dropdowns)
  |
  v
For each selected episode:
  |
  +--> Spotify: Supadata API with MP3 URL from RSS
  +--> YouTube: youtube-transcript-api (existing) -> Supadata fallback
  |
  v
Gemini analysis (existing)
  |
  v
Notion database (existing)
```

## Spotify Integration Details

### Listing Episodes (RSS Feed)

Most Spotify podcasts have a public RSS feed. To convert a Spotify show URL to an RSS feed:

1. Extract the show ID from the URL (e.g. `https://open.spotify.com/show/{show_id}`)
2. Use a free service or scrape the Spotify page to find the RSS feed URL
3. Parse the RSS feed (standard XML) to get episodes with: title, date, audio URL (MP3)

Libraries: `feedparser` for RSS parsing.

Fallback: If RSS feed cannot be found automatically, allow user to paste the RSS feed URL directly.

### Transcription

The RSS feed provides direct MP3 URLs for each episode. Supadata accepts public file URLs (MP3, M4A, etc. up to 1GB) for transcription. No audio download needed - Supadata processes server-side.

Endpoint: `GET https://api.supadata.ai/v1/youtube/transcript` with the MP3 URL (despite the path name, it accepts file URLs).

### Limitations

- Spotify-exclusive podcasts without a public RSS feed will not work
- Very long episodes may take longer for Supadata to process

## YouTube Integration (Existing)

No changes to the existing YouTube pipeline. Only addition is the range selector UI.

- Playlist listing: `yt-dlp` (existing)
- Transcript: `youtube-transcript-api` -> Supadata fallback (existing)

## UI Changes

### Platform Selector

Default: Spotify. Radio buttons at the top of the page.

### URL Input

Single text input. Placeholder changes based on platform:
- Spotify: `https://open.spotify.com/show/...`
- YouTube: `https://www.youtube.com/playlist?list=...`

Accepts both single episodes/videos and shows/playlists.

### Range Selector (new)

Shown after clicking "Carregar episodios" for shows/playlists:

1. Fetch full episode list
2. Display two dropdowns: "De" (from) and "Ate" (to)
3. Each dropdown shows: episode number + title (truncated)
4. Show count of selected episodes and time estimate
5. "Processar" button to start

For single episodes/videos: skip the range selector, process directly.

### Flow

```
1. Select platform (Spotify/YouTube)
2. Paste URL
3a. Single episode/video -> [Processar] -> process directly
3b. Show/playlist -> [Carregar episodios] -> range selector -> [Processar]
```

## New Dependencies

- `feedparser` - RSS feed parsing

## Config Changes

New Streamlit secrets:
- None required (RSS feeds are public, Supadata key already exists)

## New Module

`src/spotify.py`:
- `parse_spotify_url(url)` - extract show_id or episode_id
- `get_rss_feed_url(show_id)` - find RSS feed for a Spotify show
- `get_show_episodes(rss_url)` - parse RSS and return episode list
- `get_episode_metadata(episode)` - extract title, date, audio URL

## Files to Modify

- `streamlit_app.py` - main UI changes (platform selector, range selector, Spotify flow)
- `requirements.txt` - add `feedparser`

## Files to Create

- `src/spotify.py` - Spotify/RSS module
