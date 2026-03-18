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
    mock_response.text = json.dumps([
        {
            "nome": "John Smith",
            "cargo": "CEO",
            "empresa": "TechCorp",
            "usa_ia": "Sim - utiliza IA para automação de processos internos",
            "vai_usar_ia": "Sim - planeia expandir uso de IA generativa",
            "departamento_ai": "Não mencionado",
            "pessoas_departamento_ai": "",
            "visao_estrategica": "Transformação digital focada em cloud e IA, com expansão planeada para 2025",
            "tecnologias_mencionadas": ["ChatGPT", "AWS", "Kubernetes"],
            "principais_desafios": "Regulamentação e talento técnico",
            "outreach": "• Desafio com talento técnico\n• Interesse em IA generativa",
            "potencial_cliente": "7/10 (Quente) - Já usa IA e planeia expandir"
        }
    ])

    with patch("src.analyzer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = analyze_transcript(
            transcript="The CEO said AI is transforming...",
            metadata={"title": "CEO Interview", "description": "John Smith, CEO"},
            api_key="test-key",
        )

    assert result[0]["nome"] == "John Smith"
    assert result[0]["cargo"] == "CEO"
    assert result[0]["empresa"] == "TechCorp"
    assert "ChatGPT" in result[0]["tecnologias_mencionadas"]
    assert result[0]["usa_ia"].startswith("Sim")


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


def test_excludes_person_without_name():
    """Person with 'Não mencionado' or empty name should be excluded."""
    mock_response = MagicMock()
    mock_response.text = json.dumps([{
        "nome": "Não mencionado",
        "cargo": "CEO",
        "empresa": "TechCorp",
        "usa_ia": "Sim", "vai_usar_ia": "Não",
        "departamento_ai": "Não", "pessoas_departamento_ai": "",
        "visao_estrategica": "Visão", "tecnologias_mencionadas": ["AI"],
        "principais_desafios": "Desafios", "outreach": "• Ponto", "potencial_cliente": "5/10"
    }])
    with patch("src.analyzer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        result = analyze_transcript(transcript="text", metadata={"title": "t"}, api_key="test-key")
    assert len(result) == 0


def test_excludes_person_with_too_many_empty_fields():
    """Person with >3 required fields as 'Não mencionado' should be excluded."""
    mock_response = MagicMock()
    mock_response.text = json.dumps([{
        "nome": "John Doe", "cargo": "CTO", "empresa": "Acme",
        "usa_ia": "Não mencionado", "vai_usar_ia": "Não mencionado",
        "departamento_ai": "Não mencionado", "pessoas_departamento_ai": "",
        "visao_estrategica": "Não mencionado", "tecnologias_mencionadas": [],
        "principais_desafios": "Não mencionado", "outreach": "", "potencial_cliente": "3/10"
    }])
    with patch("src.analyzer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        result = analyze_transcript(transcript="text", metadata={"title": "t"}, api_key="test-key")
    assert len(result) == 0


def test_excludes_person_with_short_cargo_empresa():
    """Person with cargo or empresa <= 2 chars should be excluded."""
    mock_response = MagicMock()
    mock_response.text = json.dumps([{
        "nome": "Jane Doe", "cargo": "CO", "empresa": "XY",
        "usa_ia": "Sim", "vai_usar_ia": "Sim",
        "departamento_ai": "Não", "pessoas_departamento_ai": "",
        "visao_estrategica": "Visão", "tecnologias_mencionadas": ["AI"],
        "principais_desafios": "Desafios", "outreach": "• Ponto", "potencial_cliente": "6/10"
    }])
    with patch("src.analyzer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        result = analyze_transcript(transcript="text", metadata={"title": "t"}, api_key="test-key")
    assert len(result) == 0


def test_includes_valid_person():
    """Person with all valid fields should be included."""
    mock_response = MagicMock()
    mock_response.text = json.dumps([{
        "nome": "Alice Johnson", "cargo": "CPO", "empresa": "InnovateTech",
        "usa_ia": "Sim", "vai_usar_ia": "Não mencionado",
        "departamento_ai": "Sim - 5 pessoas", "pessoas_departamento_ai": "Carlos Silva (DataTeam AI)",
        "visao_estrategica": "Focus em inovação", "tecnologias_mencionadas": ["Python", "TensorFlow"],
        "principais_desafios": "Escala", "outreach": "• Desafio\n• Oportunidade", "potencial_cliente": "8/10"
    }])
    with patch("src.analyzer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        result = analyze_transcript(transcript="text", metadata={"title": "t"}, api_key="test-key")
    assert len(result) > 0
    assert result[0]["cargo"] == "CPO"
    assert result[0]["empresa"] == "InnovateTech"


def test_max_5_persons_returned():
    """Should return maximum 5 persons even if Gemini returns more."""
    persons = [{
        "nome": f"Person {i}", "cargo": "CEO", "empresa": f"Company {i}",
        "usa_ia": "Sim", "vai_usar_ia": "Não", "departamento_ai": "Não",
        "pessoas_departamento_ai": "", "visao_estrategica": "Strategy",
        "tecnologias_mencionadas": ["AI"], "principais_desafios": "Challenges",
        "outreach": "• Point", "potencial_cliente": "5/10"
    } for i in range(7)]
    mock_response = MagicMock()
    mock_response.text = json.dumps(persons)
    with patch("src.analyzer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        result = analyze_transcript(transcript="text", metadata={"title": "t"}, api_key="test-key")
    assert len(result) == 5


def test_outreach_format():
    """Outreach field should contain 3-5 bullet points starting with •"""
    mock_response = MagicMock()
    mock_response.text = json.dumps([{
        "nome": "Bob Smith", "cargo": "CEO", "empresa": "TechCorp",
        "usa_ia": "Sim", "vai_usar_ia": "Sim", "departamento_ai": "Não",
        "pessoas_departamento_ai": "", "visao_estrategica": "Strategy",
        "tecnologias_mencionadas": ["AI"], "principais_desafios": "Challenges",
        "outreach": "• Challenge with data\n• Interest in AI\n• Planning expansion",
        "potencial_cliente": "7/10"
    }])
    with patch("src.analyzer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        result = analyze_transcript(transcript="text", metadata={"title": "t"}, api_key="test-key")
    assert len(result) > 0
    outreach = result[0]["outreach"]
    lines = outreach.split('\n')
    assert len(lines) >= 3
    assert all('•' in line for line in lines)


def test_cargo_empresa_separated():
    """Cargo and empresa should be separate fields in the result."""
    mock_response = MagicMock()
    mock_response.text = json.dumps([{
        "nome": "Carol White", "cargo": "VP of Engineering", "empresa": "StartupXYZ",
        "usa_ia": "Não mencionado", "vai_usar_ia": "Não mencionado",
        "departamento_ai": "Não", "pessoas_departamento_ai": "",
        "visao_estrategica": "Strategy", "tecnologias_mencionadas": ["Cloud"],
        "principais_desafios": "Hiring", "outreach": "• Point", "potencial_cliente": "4/10"
    }])
    with patch("src.analyzer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        result = analyze_transcript(transcript="text", metadata={"title": "t"}, api_key="test-key")
    assert len(result) > 0
    assert result[0]["cargo"] == "VP of Engineering"
    assert result[0]["empresa"] == "StartupXYZ"
    assert "StartupXYZ" not in result[0]["cargo"]


def test_analyze_transcript_handles_single_dict_response():
    """Backward compatibility: single dict response should be wrapped in list."""
    mock_response = MagicMock()
    mock_response.text = json.dumps({  # Single dict, not array
        "nome": "Single Person", "cargo": "CEO", "empresa": "SoloCorp",
        "usa_ia": "Sim", "vai_usar_ia": "Não", "departamento_ai": "Não",
        "pessoas_departamento_ai": "", "visao_estrategica": "Strategy",
        "tecnologias_mencionadas": ["AI"], "principais_desafios": "Challenges",
        "outreach": "• Point", "potencial_cliente": "5/10"
    })
    with patch("src.analyzer.genai") as mock_genai:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        result = analyze_transcript(transcript="text", metadata={"title": "t"}, api_key="test-key")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["nome"] == "Single Person"
