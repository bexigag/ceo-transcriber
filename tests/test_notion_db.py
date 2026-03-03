from unittest.mock import patch, MagicMock, call
from src.notion_db import create_database, add_row, SCHEMA


def test_create_database_returns_id():
    mock_notion = MagicMock()
    mock_notion.databases.create.return_value = {"id": "db-123"}

    with patch("src.notion_db.Client", return_value=mock_notion):
        db_id = create_database(
            token="test-token",
            parent_page_id="page-456",
        )

    assert db_id == "db-123"
    mock_notion.databases.create.assert_called_once()


def test_create_database_has_correct_schema():
    mock_notion = MagicMock()
    mock_notion.databases.create.return_value = {"id": "db-123"}

    with patch("src.notion_db.Client", return_value=mock_notion):
        create_database(token="test-token", parent_page_id="page-456")

    call_kwargs = mock_notion.databases.create.call_args[1]
    properties = call_kwargs["properties"]

    assert "Nome" in properties
    assert "Cargo" in properties
    assert "Link da Entrevista" in properties
    assert "Usa IA" in properties
    assert "Vai Usar IA" in properties
    assert "Inovação" in properties
    assert "Estratégia Digital" in properties
    assert "Tecnologias Mencionadas" in properties
    assert "Principais Desafios" in properties
    assert "Resumo Estratégico" in properties
    assert "Apontamentos" in properties
    assert "Status" in properties


def test_add_row_creates_page():
    mock_notion = MagicMock()
    mock_notion.pages.create.return_value = {"id": "page-789"}

    analysis = {
        "nome": "John Smith",
        "cargo": "CEO of TechCorp",
        "usa_ia": "Sim - usa ChatGPT",
        "vai_usar_ia": "Sim - planeia expandir",
        "inovacao": "Plataforma interna de IA",
        "estrategia_digital": "Cloud-first",
        "tecnologias_mencionadas": ["ChatGPT", "AWS"],
        "principais_desafios": "Regulamentação",
        "resumo_estrategico": "Aposta forte em IA",
    }

    with patch("src.notion_db.Client", return_value=mock_notion):
        page_id = add_row(
            token="test-token",
            database_id="db-123",
            video_url="https://youtube.com/watch?v=abc",
            analysis=analysis,
        )

    assert page_id == "page-789"
    mock_notion.pages.create.assert_called_once()

    call_kwargs = mock_notion.pages.create.call_args[1]
    props = call_kwargs["properties"]
    assert props["Nome"]["title"][0]["text"]["content"] == "John Smith"
    assert props["Status"]["select"]["name"] == "Concluído"


def test_add_row_with_error_status():
    mock_notion = MagicMock()
    mock_notion.pages.create.return_value = {"id": "page-err"}

    with patch("src.notion_db.Client", return_value=mock_notion):
        page_id = add_row(
            token="test-token",
            database_id="db-123",
            video_url="https://youtube.com/watch?v=abc",
            analysis=None,
            status="Erro",
        )

    call_kwargs = mock_notion.pages.create.call_args[1]
    assert call_kwargs["properties"]["Status"]["select"]["name"] == "Erro"
