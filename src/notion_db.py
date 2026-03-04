from notion_client import Client


SCHEMA = {
    "Nome": {"title": {}},
    "Cargo": {"rich_text": {}},
    "Link da Entrevista": {"url": {}},
    "Usa IA": {"rich_text": {}},
    "Vai Usar IA": {"rich_text": {}},
    "Inovação": {"rich_text": {}},
    "Estratégia Digital": {"rich_text": {}},
    "Tecnologias Mencionadas": {"multi_select": {"options": []}},
    "Principais Desafios": {"rich_text": {}},
    "Resumo Estratégico": {"rich_text": {}},
    "Apontamentos": {"rich_text": {}},
    "Status": {
        "select": {
            "options": [
                {"name": "A Processar", "color": "yellow"},
                {"name": "Concluído", "color": "green"},
                {"name": "Erro", "color": "red"},
            ]
        }
    },
}


def create_database(token: str, parent_page_id: str) -> str:
    notion = Client(auth=token)

    database = notion.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "CEO Video Transcriber"}}],
    )

    db_id = database["id"]

    # API 2025-09-03: properties must be set on the data source
    data_source_id = database["data_sources"][0]["id"]
    notion.data_sources.update(
        data_source_id=data_source_id,
        properties=SCHEMA,
    )

    return db_id


def _get_data_source_id(notion: Client, database_id: str) -> str:
    db = notion.databases.retrieve(database_id=database_id)
    return db["data_sources"][0]["id"]


def _rich_text(content: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": content[:2000]}}]}


def add_row(
    token: str,
    database_id: str,
    video_url: str,
    analysis: dict | None,
    status: str = "Concluído",
) -> str:
    notion = Client(auth=token)
    data_source_id = _get_data_source_id(notion, database_id)

    properties = {
        "Link da Entrevista": {"url": video_url},
        "Status": {"select": {"name": status}},
    }

    if analysis:
        properties["Nome"] = {
            "title": [{"type": "text", "text": {"content": analysis.get("nome", "Desconhecido")}}]
        }
        properties["Cargo"] = _rich_text(analysis.get("cargo", ""))
        properties["Usa IA"] = _rich_text(analysis.get("usa_ia", ""))
        properties["Vai Usar IA"] = _rich_text(analysis.get("vai_usar_ia", ""))
        properties["Inovação"] = _rich_text(analysis.get("inovacao", ""))
        properties["Estratégia Digital"] = _rich_text(analysis.get("estrategia_digital", ""))
        properties["Principais Desafios"] = _rich_text(analysis.get("principais_desafios", ""))
        properties["Resumo Estratégico"] = _rich_text(analysis.get("resumo_estrategico", ""))

        techs = analysis.get("tecnologias_mencionadas", [])
        if isinstance(techs, list):
            # Notion multi-select doesn't allow commas in option names
            properties["Tecnologias Mencionadas"] = {
                "multi_select": [{"name": t.replace(",", " e")[:100]} for t in techs if isinstance(t, str)]
            }
    else:
        properties["Nome"] = {
            "title": [{"type": "text", "text": {"content": "Erro no processamento"}}]
        }

    page = notion.pages.create(
        parent={"type": "data_source_id", "data_source_id": data_source_id},
        properties=properties,
    )

    return page["id"]
