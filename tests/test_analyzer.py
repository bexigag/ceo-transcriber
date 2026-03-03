import json
from unittest.mock import patch, MagicMock
from src.analyzer import analyze_transcript, build_prompt


def test_build_prompt_includes_transcript_and_metadata():
    prompt = build_prompt(
        transcript="The CEO said AI is transforming our business...",
        metadata={"title": "CEO Interview", "description": "John Smith talks AI"}
    )

    assert "The CEO said AI is transforming our business" in prompt
    assert "CEO Interview" in prompt
    assert "John Smith talks AI" in prompt


def test_analyze_transcript_returns_structured_data():
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "nome": "John Smith",
        "cargo": "CEO of TechCorp",
        "usa_ia": "Sim - utiliza IA para automação de processos internos",
        "vai_usar_ia": "Sim - planeia expandir uso de IA generativa",
        "inovacao": "Desenvolvimento de plataforma interna de IA",
        "estrategia_digital": "Transformação digital focada em cloud e IA",
        "tecnologias_mencionadas": ["ChatGPT", "AWS", "Kubernetes"],
        "principais_desafios": "Regulamentação e talento técnico",
        "resumo_estrategico": "TechCorp aposta forte em IA generativa..."
    })

    with patch("src.analyzer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = analyze_transcript(
            transcript="The CEO said AI is transforming...",
            metadata={"title": "CEO Interview", "description": "John Smith, CEO"},
            api_key="test-key",
        )

    assert result["nome"] == "John Smith"
    assert result["cargo"] == "CEO of TechCorp"
    assert "ChatGPT" in result["tecnologias_mencionadas"]
    assert result["usa_ia"].startswith("Sim")


def test_analyze_transcript_handles_invalid_json():
    mock_response = MagicMock()
    mock_response.text = "This is not JSON"

    with patch("src.analyzer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = analyze_transcript(
            transcript="text",
            metadata={"title": "t", "description": "d"},
            api_key="test-key",
        )

    assert result is None
