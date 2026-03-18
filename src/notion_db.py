from notion_client import Client


SCHEMA = {
    "Nome": {"title": {}},
    "Cargo": {"rich_text": {}},
    "Link da Entrevista": {"url": {}},
    "Data": {"date": {}},
    "Potencial Cliente": {"rich_text": {}},
    "Usa IA": {"rich_text": {}},
    "Vai Usar IA": {"rich_text": {}},
    "Visão Estratégica": {"rich_text": {}},
    "Tecnologias Mencionadas": {"multi_select": {"options": []}},
    "Principais Desafios": {"rich_text": {}},
    "Tem Departamento AI": {"rich_text": {}},
    "Pessoas Departamento AI": {"rich_text": {}},
    "Outreach": {"rich_text": {}},
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
    "Nome da Empresa": {"rich_text": {}},
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


def _parse_date(date_str: str) -> str | None:
    """Parse date string to ISO format (YYYY-MM-DD) for Notion."""
    if not date_str:
        return None
    # ISO format: 2026-03-02T06:05:00Z
    if "T" in date_str:
        return date_str[:10]
    # YouTube format: YYYYMMDD
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return None


def add_row(
    token: str,
    database_id: str,
    video_url: str,
    analysis: dict | None,
    status: str = "Concluído",
    date: str = "",
) -> str:
    notion = Client(auth=token)
    data_source_id = _get_data_source_id(notion, database_id)

    properties = {
        "Link da Entrevista": {"url": video_url},
        "Status": {"select": {"name": status}},
    }

    parsed_date = _parse_date(date)
    if parsed_date:
        properties["Data"] = {"date": {"start": parsed_date}}

    if analysis:
        properties["Nome"] = {
            "title": [{"type": "text", "text": {"content": analysis.get("nome", "Desconhecido")}}]
        }
        properties["Cargo"] = _rich_text(analysis.get("cargo", ""))
        properties["Nome da Empresa"] = _rich_text(analysis.get("empresa") or "Não mencionado")
        properties["Usa IA"] = _rich_text(analysis.get("usa_ia", ""))
        properties["Vai Usar IA"] = _rich_text(analysis.get("vai_usar_ia", ""))
        properties["Visão Estratégica"] = _rich_text(analysis.get("visao_estrategica") or "Não mencionado")
        properties["Principais Desafios"] = _rich_text(analysis.get("principais_desafios", ""))
        properties["Potencial Cliente"] = _rich_text(analysis.get("potencial_cliente", ""))
        properties["Tem Departamento AI"] = _rich_text(analysis.get("departamento_ai") or "Não mencionado")
        properties["Pessoas Departamento AI"] = _rich_text(analysis.get("pessoas_departamento_ai") or "")
        properties["Outreach"] = _rich_text(analysis.get("outreach") or "")

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
