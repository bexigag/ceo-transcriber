import time
import requests
import streamlit as st

from src.youtube import parse_youtube_url, extract_video_id, get_transcript, get_video_metadata, get_playlist_video_ids
from src.analyzer import analyze_transcript
from src.notion_db import add_row


def get_transcript_supadata(video_id: str, api_key: str) -> str | None:
    """Fallback transcript fetcher using Supadata API. Tries pt, then en, then any language."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    for lang in ["pt", "en", None]:
        try:
            params = {"url": url}
            if lang:
                params["lang"] = lang
            resp = requests.get(
                "https://api.supadata.ai/v1/youtube/transcript",
                params=params,
                headers={"x-api-key": api_key},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("content", [])
            if isinstance(content, list) and content:
                text = " ".join(item.get("text", "") for item in content)
                if text.strip():
                    return text
        except Exception:
            continue
    return None

st.set_page_config(page_title="CEO Video Transcriber", page_icon="🎥", layout="centered")


def check_password():
    if st.session_state.get("authenticated"):
        return True

    st.title("CEO Video Transcriber")
    password = st.text_input("Password", type="password")
    if st.button("Entrar"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Password incorreta.")
    return False


if not check_password():
    st.stop()


def process_single_video(video_id: str, gemini_key: str, notion_token: str, database_id: str):
    """Process one video. Returns (success: bool, analysis: dict | None, page_id: str | None)."""
    with st.status("A processar o video...", expanded=True) as status:
        st.write("A obter metadados...")
        try:
            metadata = get_video_metadata(video_id)
        except Exception as e:
            st.error(f"Erro ao obter metadados: {e}")
            status.update(label="Erro nos metadados", state="error")
            return False, None, None
        st.write(f"**{metadata['title']}**")

        st.write("A obter transcricao...")
        transcript = get_transcript(video_id)
        if transcript is None:
            supadata_key = st.secrets.get("SUPADATA_API_KEY")
            if supadata_key:
                st.write("A tentar via Supadata...")
                transcript = get_transcript_supadata(video_id, supadata_key)
        if transcript is None:
            st.error("Nao foi possivel obter a transcricao. O video pode nao ter legendas.")
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
        try:
            analysis = analyze_transcript(transcript, metadata, gemini_key)
        except Exception as e:
            st.warning(f"Erro do Gemini: {e}")
            analysis = None
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


GEMINI_WAIT_SECONDS = 20  # 5 RPM limit = 1 request per 12s, using 20s for safety
GEMINI_DAILY_LIMIT = 20


def process_playlist(playlist_id: str, gemini_key: str, notion_token: str, database_id: str):
    """Process all videos in a playlist."""
    with st.spinner("A obter lista de videos da playlist..."):
        videos = get_playlist_video_ids(playlist_id)

    total = len(videos)
    if total > GEMINI_DAILY_LIMIT:
        st.warning(
            f"A playlist tem **{total}** videos mas o limite diario do Gemini e **{GEMINI_DAILY_LIMIT}**. "
            f"Vao ser processados apenas os primeiros {GEMINI_DAILY_LIMIT}."
        )
        videos = videos[:GEMINI_DAILY_LIMIT]

    st.info(f"A processar **{len(videos)}** videos (~{len(videos) * GEMINI_WAIT_SECONDS // 60} minutos estimados).")

    progress = st.progress(0, text="A iniciar...")
    success_count = 0
    error_count = 0
    results = []

    for i, video in enumerate(videos):
        progress.progress(i / len(videos), text=f"Video {i + 1}/{len(videos)}: {video['title'][:50]}")

        st.subheader(f"Video {i + 1}: {video['title'][:80]}")
        ok, analysis, page_id = process_single_video(video["id"], gemini_key, notion_token, database_id)

        if ok:
            success_count += 1
            results.append({"video": video["title"], "status": "OK", "nome": analysis.get("nome", "—")})
        else:
            error_count += 1
            results.append({"video": video["title"], "status": "Erro", "nome": "—"})

        # Wait between videos to respect Gemini rate limits (5 RPM)
        if i < len(videos) - 1:
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


# --- Main UI ---

st.title("CEO Video Transcriber")
st.markdown("Cola um link do YouTube (video ou playlist) para analisar entrevistas de CEOs.")

url = st.text_input("URL do YouTube", placeholder="https://www.youtube.com/watch?v=...")

if st.button("Processar", type="primary", disabled=not url):
    gemini_key = st.secrets["GEMINI_API_KEY"]
    notion_token = st.secrets["NOTION_TOKEN"]
    database_id = st.secrets["NOTION_DATABASE_ID"]

    try:
        parsed = parse_youtube_url(url)
    except ValueError as e:
        st.error(f"URL invalido: {e}")
        st.stop()

    if parsed["type"] == "playlist":
        process_playlist(parsed["playlist_id"], gemini_key, notion_token, database_id)
    else:
        ok, analysis, page_id = process_single_video(
            parsed["video_id"], gemini_key, notion_token, database_id
        )
        if ok:
            st.success("Video processado com sucesso!")
            clean_id = page_id.replace("-", "")
            st.markdown(f"[Abrir no Notion](https://notion.so/{clean_id})")
            st.subheader("Resultado da Analise")
            st.json(analysis)
