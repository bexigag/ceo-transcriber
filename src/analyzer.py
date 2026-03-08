import json
from google import genai
from google.genai import types


SYSTEM_PROMPT = """És um analista de inteligência estratégica. Analisa transcrições de entrevistas de CEOs e extrai informação estruturada, para a nossa empresa que implementa AI e faz software, tirar vantagem.

Responde APENAS com um objeto JSON válido, sem texto adicional. O JSON deve ter exatamente estes campos:

{
  "nome": "Nome completo do CEO/entrevistado",
  "cargo": "Cargo e empresa",
  "usa_ia": "Sim/Não - informaçao extra sobre isto",
  "vai_usar_ia": "Sim/Não - informaçao extra sobre isto",
  "inovacao": "Inovações em curso",
  "estrategia_digital": "Insights sobre estratégia digital",
  "tecnologias_mencionadas": ["lista", "de", "tecnologias", "os elementos nao podem ter virgulas"],
  "principais_desafios": "Desafios principais",
  "resumo_estrategico": "Resumo conciso (2-3 frases)"
}

Se algum campo não puder ser determinado, usa "Não mencionado".
Responde em Português."""


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
            max_output_tokens=8192,
        ),
    )

    try:
        response_text = response.text.strip()
        # Remove markdown code block wrapping (```json ... ```)
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            response_text = "\n".join(lines)
        return json.loads(response_text)
    except (json.JSONDecodeError, IndexError, AttributeError):
        return None
