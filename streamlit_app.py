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


def get_transcript_supadata_file(audio_url: str, api_key: str, max_polls: int = 30) -> tuple[str | None, str | None]:
    """Transcribe an audio file URL using Supadata API. Returns (transcript, error_detail)."""
    try:
        resp = requests.get(
            "https://api.supadata.ai/v1/transcript",
            params={"url": audio_url, "text": "true"},
            headers={"x-api-key": api_key},
            timeout=120,
        )

        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", "")
            if content.strip():
                return content, None
            return None, f"Supadata devolveu conteudo vazio. Resposta: {resp.text[:300]}"

        if resp.status_code == 202:
            job_id = resp.json().get("jobId")
            if not job_id:
                return None, "Supadata devolveu 202 mas sem jobId"
            for poll_num in range(max_polls):
                time.sleep(10)
                poll_resp = requests.get(
                    f"https://api.supadata.ai/v1/transcript/{job_id}",
                    headers={"x-api-key": api_key},
                    timeout=30,
                )
                if poll_resp.status_code == 200:
                    data = poll_resp.json()
                    content = data.get("content", "")
                    if content.strip():
                        return content, None
                    return None, f"Job concluido mas conteudo vazio"
            return None, f"Timeout: job {job_id} nao completou apos {max_polls} tentativas"

        return None, f"Status {resp.status_code}: {resp.text[:300]}"
    except Exception as e:
        return None, f"Excepcao: {e}"

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
        gemini_keys = [k.strip() for k in gemini_key.split(",") if k.strip()]
        gemini_keys.reverse()  # Use last key first (first key reserved for Make.com)
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

        transcript, error_detail = get_transcript_supadata_file(episode["audio_url"], supadata_key)
        if transcript is None:
            st.error(f"Nao foi possivel transcrever o episodio. {error_detail or ''}")
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


GEMINI_WAIT_SECONDS = 20  # 5 RPM limit = 1 request per 12s, using 20s for safety


# --- Main UI ---


def main_ui():
    st.title("CEO Video Transcriber")

    platform = st.radio("Plataforma", ["O CEO e o Limite", "YouTube"], horizontal=True)

    if platform == "O CEO e o Limite":
        st.markdown("Podcast da Catia Mateus no Expresso. Os episodios sao carregados automaticamente.")

        if "ceo_episodes" not in st.session_state:
            if st.button("Carregar episodios"):
                with st.spinner("A carregar episodios..."):
                    from src.podcast import get_ceo_episodes
                    try:
                        episodes = get_ceo_episodes()
                    except Exception as e:
                        st.error(f"Erro ao carregar episodios: {e}")
                        return
                if not episodes:
                    st.error("Nenhum episodio encontrado.")
                    return
                st.session_state.ceo_episodes = episodes
                st.rerun()
            return

        episodes = st.session_state.ceo_episodes
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
            return

        selected = episodes[from_idx:to_idx + 1]
        st.info(f"**{len(selected)}** episodios selecionados (~{len(selected) * GEMINI_WAIT_SECONDS // 60} minutos estimados).")

        gemini_key = st.secrets["GEMINI_API_KEY"]
        notion_token = st.secrets["NOTION_TOKEN"]
        database_id = st.secrets["NOTION_DATABASE_ID"]

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

    else:
        st.markdown("Cola um link do YouTube (video ou playlist) para analisar entrevistas de CEOs.")
        url = st.text_input("URL do YouTube", placeholder="https://www.youtube.com/watch?v=...")

        if not url:
            return

        gemini_key = st.secrets["GEMINI_API_KEY"]
        notion_token = st.secrets["NOTION_TOKEN"]
        database_id = st.secrets["NOTION_DATABASE_ID"]

        try:
            parsed = parse_youtube_url(url)
        except ValueError as e:
            st.error(f"URL invalido: {e}")
            return

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
                        return
                    st.session_state.yt_videos = videos
                    st.session_state.yt_playlist_id = parsed["playlist_id"]
                    st.rerun()
                return

            videos = st.session_state.yt_videos
            st.success(f"**{len(videos)}** videos encontrados.")

            yt_options = [f"{i + 1}. {v['title'][:80]}" for i, v in enumerate(videos)]

            col1, col2 = st.columns(2)
            with col1:
                from_idx = st.selectbox("De", range(len(yt_options)), format_func=lambda i: yt_options[i], index=0)
            with col2:
                default_to = min(from_idx + 4, len(yt_options) - 1)
                to_idx = st.selectbox("Ate", range(len(yt_options)), format_func=lambda i: yt_options[i], index=default_to)

            if from_idx > to_idx:
                st.error("O video 'De' deve ser anterior ou igual ao 'Ate'.")
                return

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


main_ui()
