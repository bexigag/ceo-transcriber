import json
from google import genai
from google.genai import types


SYSTEM_PROMPT = """És um analista de inteligência estratégica. Analisa transcrições de entrevistas de CEOs e extrai informação estruturada.

Responde APENAS com um objeto JSON válido, sem texto adicional. O JSON deve ter exatamente estes campos:

{
  "nome": "Nome completo do CEO/entrevistado",
  "cargo": "Cargo e empresa",
  "usa_ia": "Sim/Não - breve explicação de como usa IA atualmente",
  "vai_usar_ia": "Sim/Não - breve explicação da intenção futura",
  "inovacao": "Inovações em curso mencionadas",
  "estrategia_digital": "Insights sobre estratégia digital",
  "tecnologias_mencionadas": ["lista", "de", "tecnologias"],
  "principais_desafios": "Desafios principais discutidos",
  "resumo_estrategico": "Resumo estratégico conciso (2-3 frases)"
}

Se algum campo não puder ser determinado a partir da transcrição, usa "Não mencionado".
Responde sempre em Português."""


def build_prompt(transcript: str, metadata: dict) -> str:
    return f"""Analisa a seguinte entrevista de CEO.

Título do vídeo: {metadata.get('title', 'Desconhecido')}
Descrição: {metadata.get('description', 'Sem descrição')}

Transcrição:
{transcript}"""


def analyze_transcript(transcript: str, metadata: dict, api_key: str) -> dict | None:
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_prompt(transcript, metadata),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=2048,
        ),
    )

    try:
        response_text = response.text
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(response_text)
    except (json.JSONDecodeError, IndexError, AttributeError):
        return None
