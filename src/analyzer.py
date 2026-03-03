import json
from anthropic import Anthropic


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
    client = Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": build_prompt(transcript, metadata)}
        ],
    )

    try:
        response_text = message.content[0].text
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(response_text)
    except (json.JSONDecodeError, IndexError):
        return None
