import json
from google import genai
from google.genai import types


SYSTEM_PROMPT = """És um analista de inteligência estratégica. Analisa transcrições de entrevistas de CEOs e extrai informação estruturada.

Responde APENAS com um objeto JSON válido, sem texto adicional. O JSON deve ter exatamente estes campos:

{
  "nome": "Nome completo do CEO/entrevistado",
  "cargo": "Cargo e empresa",
  "usa_ia": "Sim/Não - explicação detalhada: em que áreas usa IA, que ferramentas ou soluções específicas, para que processos, e que resultados obteve",
  "vai_usar_ia": "Sim/Não - explicação detalhada: em que áreas pretende usar IA, que planos concretos tem, que investimentos ou parcerias prevê, e qual o horizonte temporal",
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
