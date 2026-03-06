# Spotify/Podcast Support + Range Selector Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add podcast support via RSS feeds with Supadata transcription, plus a range selector for both platforms.

**Architecture:** RSS feeds provide episode listings and direct audio URLs. Supadata transcribes audio files by URL (no download needed). Streamlit UI gets a platform toggle (Podcast RSS / YouTube), range selector with two dropdowns, and a new processing flow for podcast episodes.

**Tech Stack:** Python, Streamlit, feedparser (RSS), Supadata API, Gemini, Notion API

**Design note:** Research showed that auto-discovering RSS feeds from Spotify URLs is unreliable (spotifeed is dead, SpotifyScraper doesn't support podcasts, Spotify API requires Premium). The user pastes the RSS feed URL directly. Most podcasts publish their RSS feed on their website or hosting platform.

---

### Task 1: Create `src/podcast.py` - RSS feed parser

**Files:**
- Create: `src/podcast.py`
- Create: `tests/test_podcast.py`

**Step 1: Write failing tests**

```python
# tests/test_podcast.py
import pytest
from src.podcast import parse_podcast_url, get_show_episodes


def test_parse_rss_url():
    result = parse_podcast_url("https://feeds.example.com/podcast.xml")
    assert result == {"type": "show", "rss_url": "https://feeds.example.com/podcast.xml"}


def test_parse_rss_url_strips_whitespace():
    result = parse_podcast_url("  https://feeds.example.com/podcast.xml  ")
    assert result == {"type": "show", "rss_url": "https://feeds.example.com/podcast.xml"}


def test_parse_empty_url_raises():
    with pytest.raises(ValueError):
        parse_podcast_url("")
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_podcast.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/podcast.py
import feedparser


def parse_podcast_url(url: str) -> dict:
    url = url.strip()
    if not url:
        raise ValueError("URL vazio")
    return {"type": "show", "rss_url": url}


def get_show_episodes(rss_url: str) -> list[dict]:
    feed = feedparser.parse(rss_url)

    if feed.bozo and not feed.entries:
        raise ValueError(f"Nao foi possivel ler o RSS feed: {rss_url}")

    episodes = []
    for entry in feed.entries:
        audio_url = None
        for link in entry.get("links", []):
            if link.get("type", "").startswith("audio/") or link.get("rel") == "enclosure":
                audio_url = link.get("href")
                break
        if not audio_url:
            for enc in entry.get("enclosures", []):
                audio_url = enc.get("href")
                break

        episodes.append({
            "title": entry.get("title", "Sem titulo"),
            "published": entry.get("published", ""),
            "audio_url": audio_url,
            "link": entry.get("link", ""),
        })

    return episodes


def get_episode_metadata(episode: dict) -> dict:
    return {
        "title": episode.get("title", "Sem titulo"),
        "description": "",
        "uploader": "",
        "upload_date": episode.get("published", ""),
        "url": episode.get("link", episode.get("audio_url", "")),
    }
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_podcast.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/podcast.py tests/test_podcast.py
git commit -m "feat: add podcast RSS feed parser"
```

---

### Task 2: Add Supadata file URL transcription

**Files:**
- Modify: `streamlit_app.py` (add new function after `get_transcript_supadata`)

**Step 1: Write failing test**

```python
# tests/test_podcast.py (append to existing)
from unittest.mock import patch, MagicMock


def test_get_transcript_supadata_file_success():
    from streamlit_app import get_transcript_supadata_file

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"content": "transcribed text here", "lang": "pt"}

    with patch("streamlit_app.requests.get", return_value=mock_resp) as mock_get:
        result = get_transcript_supadata_file("https://example.com/ep.mp3", "fake-key")
        assert result == "transcribed text here"
        mock_get.assert_called_once()


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
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_podcast.py::test_get_transcript_supadata_file_success -v`
Expected: FAIL (function doesn't exist)

**Step 3: Write implementation**

Add this function to `streamlit_app.py` after the existing `get_transcript_supadata` function:

```python
def get_transcript_supadata_file(audio_url: str, api_key: str, max_polls: int = 30) -> str | None:
    """Transcribe an audio file URL using Supadata API. Handles async jobs for large files."""
    try:
        resp = requests.get(
            "https://api.supadata.ai/v1/transcript",
            params={"url": audio_url, "text": "true"},
            headers={"x-api-key": api_key},
            timeout=60,
        )

        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", "")
            return content if content.strip() else None

        if resp.status_code == 202:
            job_id = resp.json().get("jobId")
            if not job_id:
                return None
            for _ in range(max_polls):
                time.sleep(10)
                poll_resp = requests.get(
                    f"https://api.supadata.ai/v1/transcript/{job_id}",
                    headers={"x-api-key": api_key},
                    timeout=30,
                )
                if poll_resp.status_code == 200:
                    data = poll_resp.json()
                    content = data.get("content", "")
                    return content if content.strip() else None
            return None

        return None
    except Exception:
        return None
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_podcast.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add streamlit_app.py tests/test_podcast.py
git commit -m "feat: add Supadata file URL transcription with async polling"
```

---

### Task 3: Add `process_single_episode` for podcast episodes

**Files:**
- Modify: `streamlit_app.py` (add new function)

**Step 1: Write the function**

Add to `streamlit_app.py` after `process_single_video`:

```python
def process_single_episode(episode: dict, gemini_key: str, notion_token: str, database_id: str):
    """Process one podcast episode. Returns (success: bool, analysis: dict | None, page_id: str | None)."""
    from src.podcast import get_episode_metadata

    with st.status("A processar o episodio...", expanded=True) as status:
        metadata = get_episode_metadata(episode)
        st.write(f"**{metadata['title']}**")

        if not episode.get("audio_url"):
            st.error("Episodio sem URL de audio.")
            status.update(label="Sem audio", state="error")
            return False, None, None

        st.write("A transcrever via Supadata...")
        supadata_key = st.secrets.get("SUPADATA_API_KEY")
        if not supadata_key:
            st.error("SUPADATA_API_KEY nao configurada.")
            status.update(label="Sem chave Supadata", state="error")
            return False, None, None

        transcript = get_transcript_supadata_file(episode["audio_url"], supadata_key)
        if transcript is None:
            st.error("Nao foi possivel transcrever o episodio.")
            page_id = add_row(
                token=notion_token,
                database_id=database_id,
                video_url=metadata["url"],
                analysis=None,
                status="Erro",
            )
            status.update(label="Erro na transcricao", state="error")
            return False, None, page_id
        st.write(f"Transcricao: {len(transcript)} caracteres")

        st.write("A analisar com Gemini...")
        gemini_keys = [k.strip() for k in gemini_key.split(",") if k.strip()]
        gemini_keys.reverse()
        analysis = None
        for i, key in enumerate(gemini_keys):
            try:
                analysis = analyze_transcript(transcript, metadata, key)
                if analysis:
                    break
            except Exception as e:
                if i < len(gemini_keys) - 1:
                    st.warning(f"Gemini key {i + 1} falhou, a tentar a seguinte...")
                else:
                    st.warning(f"Erro do Gemini: {e}")
        if analysis is None:
            st.error("A analise do Gemini falhou.")
            page_id = add_row(
                token=notion_token,
                database_id=database_id,
                video_url=metadata["url"],
                analysis=None,
                status="Erro",
            )
            status.update(label="Erro na analise", state="error")
            return False, None, page_id

        st.write("A escrever no Notion...")
        try:
            page_id = add_row(
                token=notion_token,
                database_id=database_id,
                video_url=metadata["url"],
                analysis=analysis,
            )
        except Exception as e:
            st.error(f"Erro ao escrever no Notion: {e}")
            status.update(label="Erro no Notion", state="error")
            return False, None, None
        status.update(label="Concluido!", state="complete")

    return True, analysis, page_id
```

**Step 2: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: add process_single_episode for podcast episodes"
```

---

### Task 4: Rewrite the main UI with platform selector and range selector

**Files:**
- Modify: `streamlit_app.py` (replace the `# --- Main UI ---` section, lines 185-215)

**Step 1: Replace the main UI section**

Replace everything from `# --- Main UI ---` (line 185) to end of file with:

```python
# --- Main UI ---

st.title("CEO Video Transcriber")

platform = st.radio("Plataforma", ["Podcast (RSS)", "YouTube"], horizontal=True)

if platform == "Podcast (RSS)":
    st.markdown("Cola o URL do RSS feed do podcast. Podes encontrar o RSS no site do podcast ou na plataforma de hosting.")
    url = st.text_input("URL do RSS Feed", placeholder="https://feeds.example.com/podcast.xml")
else:
    st.markdown("Cola um link do YouTube (video ou playlist) para analisar entrevistas de CEOs.")
    url = st.text_input("URL do YouTube", placeholder="https://www.youtube.com/watch?v=...")

if not url:
    st.stop()

gemini_key = st.secrets["GEMINI_API_KEY"]
notion_token = st.secrets["NOTION_TOKEN"]
database_id = st.secrets["NOTION_DATABASE_ID"]

# --- Podcast (RSS) flow ---
if platform == "Podcast (RSS)":
    from src.podcast import parse_podcast_url, get_show_episodes, get_episode_metadata

    try:
        parsed = parse_podcast_url(url)
    except ValueError as e:
        st.error(f"URL invalido: {e}")
        st.stop()

    if "episodes" not in st.session_state or st.session_state.get("rss_url") != url:
        if st.button("Carregar episodios"):
            with st.spinner("A carregar episodios do RSS feed..."):
                try:
                    episodes = get_show_episodes(parsed["rss_url"])
                except Exception as e:
                    st.error(f"Erro ao ler o RSS feed: {e}")
                    st.stop()
            if not episodes:
                st.error("Nenhum episodio encontrado no feed.")
                st.stop()
            st.session_state.episodes = episodes
            st.session_state.rss_url = url
            st.rerun()
        st.stop()

    episodes = st.session_state.episodes
    st.success(f"**{len(episodes)}** episodios encontrados.")

    options = [f"{i + 1}. {ep['title'][:80]}" for i, ep in enumerate(episodes)]

    col1, col2 = st.columns(2)
    with col1:
        from_idx = st.selectbox("De", range(len(options)), format_func=lambda i: options[i], index=0)
    with col2:
        default_to = min(from_idx + 4, len(options) - 1)
        to_idx = st.selectbox("Ate", range(len(options)), format_func=lambda i: options[i], index=default_to)

    if from_idx > to_idx:
        st.error("O episodio 'De' deve ser anterior ou igual ao 'Ate'.")
        st.stop()

    selected = episodes[from_idx:to_idx + 1]
    st.info(f"**{len(selected)}** episodios selecionados (~{len(selected) * GEMINI_WAIT_SECONDS // 60} minutos estimados).")

    if st.button("Processar", type="primary"):
        progress = st.progress(0, text="A iniciar...")
        success_count = 0
        error_count = 0
        results = []

        for i, episode in enumerate(selected):
            progress.progress(i / len(selected), text=f"Episodio {i + 1}/{len(selected)}: {episode['title'][:50]}")
            st.subheader(f"Episodio {i + 1}: {episode['title'][:80]}")

            ok, analysis, page_id = process_single_episode(episode, gemini_key, notion_token, database_id)

            if ok:
                success_count += 1
                results.append({"episodio": episode["title"][:50], "status": "OK", "nome": analysis.get("nome", "—")})
            else:
                error_count += 1
                results.append({"episodio": episode["title"][:50], "status": "Erro", "nome": "—"})

            if i < len(selected) - 1:
                wait_msg = st.empty()
                for sec in range(GEMINI_WAIT_SECONDS, 0, -1):
                    wait_msg.info(f"A aguardar {sec}s antes do proximo episodio (limite Gemini)...")
                    time.sleep(1)
                wait_msg.empty()

        progress.progress(1.0, text="Concluido!")
        st.divider()
        st.subheader("Resumo")
        st.success(f"**{success_count}** processados com sucesso, **{error_count}** erros")
        st.table(results)

# --- YouTube flow ---
else:
    try:
        parsed = parse_youtube_url(url)
    except ValueError as e:
        st.error(f"URL invalido: {e}")
        st.stop()

    if parsed["type"] == "video":
        if st.button("Processar", type="primary"):
            ok, analysis, page_id = process_single_video(
                parsed["video_id"], gemini_key, notion_token, database_id
            )
            if ok:
                st.success("Video processado com sucesso!")
                clean_id = page_id.replace("-", "")
                st.markdown(f"[Abrir no Notion](https://notion.so/{clean_id})")
                st.subheader("Resultado da Analise")
                st.json(analysis)

    elif parsed["type"] == "playlist":
        if "yt_videos" not in st.session_state or st.session_state.get("yt_playlist_id") != parsed["playlist_id"]:
            if st.button("Carregar videos"):
                with st.spinner("A obter lista de videos da playlist..."):
                    videos = get_playlist_video_ids(parsed["playlist_id"])
                if not videos:
                    st.error("Nenhum video encontrado na playlist.")
                    st.stop()
                st.session_state.yt_videos = videos
                st.session_state.yt_playlist_id = parsed["playlist_id"]
                st.rerun()
            st.stop()

        videos = st.session_state.yt_videos
        st.success(f"**{len(videos)}** videos encontrados.")

        options = [f"{i + 1}. {v['title'][:80]}" for i, v in enumerate(videos)]

        col1, col2 = st.columns(2)
        with col1:
            from_idx = st.selectbox("De", range(len(options)), format_func=lambda i: options[i], index=0)
        with col2:
            default_to = min(from_idx + 4, len(options) - 1)
            to_idx = st.selectbox("Ate", range(len(options)), format_func=lambda i: options[i], index=default_to)

        if from_idx > to_idx:
            st.error("O video 'De' deve ser anterior ou igual ao 'Ate'.")
            st.stop()

        selected = videos[from_idx:to_idx + 1]
        st.info(f"**{len(selected)}** videos selecionados (~{len(selected) * GEMINI_WAIT_SECONDS // 60} minutos estimados).")

        if st.button("Processar", type="primary"):
            progress = st.progress(0, text="A iniciar...")
            success_count = 0
            error_count = 0
            results = []

            for i, video in enumerate(selected):
                progress.progress(i / len(selected), text=f"Video {i + 1}/{len(selected)}: {video['title'][:50]}")
                st.subheader(f"Video {i + 1}: {video['title'][:80]}")

                ok, analysis, page_id = process_single_video(video["id"], gemini_key, notion_token, database_id)

                if ok:
                    success_count += 1
                    results.append({"video": video["title"][:50], "status": "OK", "nome": analysis.get("nome", "—")})
                else:
                    error_count += 1
                    results.append({"video": video["title"][:50], "status": "Erro", "nome": "—"})

                if i < len(selected) - 1:
                    wait_msg = st.empty()
                    for sec in range(GEMINI_WAIT_SECONDS, 0, -1):
                        wait_msg.info(f"A aguardar {sec}s antes do proximo video (limite Gemini)...")
                        time.sleep(1)
                    wait_msg.empty()

            progress.progress(1.0, text="Concluido!")
            st.divider()
            st.subheader("Resumo")
            st.success(f"**{success_count}** processados com sucesso, **{error_count}** erros")
            st.table(results)
```

**Step 2: Commit**

```bash
git add streamlit_app.py
git commit -m "feat: add platform selector and range selector UI"
```

---

### Task 5: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

**Step 1: Add feedparser**

Add this line to `requirements.txt`:

```
feedparser>=6.0.0
```

**Step 2: Commit**

```bash
git add requirements.txt
git commit -m "feat: add feedparser dependency"
```

---

### Task 6: Update design doc with final approach

**Files:**
- Modify: `docs/plans/2026-03-06-spotify-migration-design.md`

**Step 1: Update the design doc**

Update the design doc to reflect the final approach:
- Platform name changed from "Spotify" to "Podcast (RSS)"
- User pastes RSS feed URL directly (no auto-discovery from Spotify URLs)
- Supadata endpoint is `GET /v1/transcript` with file URLs
- Async job polling for large files

**Step 2: Commit**

```bash
git add docs/plans/2026-03-06-spotify-migration-design.md
git commit -m "docs: update design to reflect RSS feed approach"
```

---

### Task 7: Manual end-to-end test

**Step 1: Find a test RSS feed**

Find a podcast with a public RSS feed. Example: search for any popular podcast name + "RSS feed".

**Step 2: Test podcast flow**

1. Run `streamlit run streamlit_app.py`
2. Select "Podcast (RSS)"
3. Paste the RSS feed URL
4. Click "Carregar episodios"
5. Verify episode list loads
6. Select a range (De/Ate)
7. Click "Processar"
8. Verify transcription and Notion write work

**Step 3: Test YouTube flow**

1. Select "YouTube"
2. Paste a YouTube playlist URL
3. Click "Carregar videos"
4. Select a range
5. Click "Processar"
6. Verify existing pipeline still works

**Step 4: Test single video (YouTube)**

1. Paste a single YouTube video URL
2. Click "Processar"
3. Verify it processes without range selector
