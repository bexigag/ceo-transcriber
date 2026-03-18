import json
from google import genai
from google.genai import types


SYSTEM_PROMPT = """És um analista de inteligência estratégica. Analisa transcrições de entrevistas e identifica pessoas com substância suficiente para preencher os campos abaixo.

A nossa empresa implementa soluções de AI, ensina a usar AI e otimiza processos com AI. O objetivo é identificar oportunidades de negócio nestas entrevistas.

REGRAS IMPORTANTES:
- Exclui apresentadores/entrevistadores que apenas fazem perguntas sem partilhar opiniões.
- Identifica pessoas com nome MENCIONADO, cargo numa empresa e informação suficiente.
- Se NOME for "Não mencionado" ou vazio, EXCLUIR a pessoa.
- Se CARGO ou EMPRESA tiverem <= 2 caracteres, EXCLUIR a pessoa.
- Se mais de 3 campos obrigatórios estiverem "Não mencionado", EXCLUIR a pessoa.
- Máximo de 5 pessoas por entrevista.

Separação CARGO/EMPRESA:
- "cargo": Apenas o título/função (ex: "CEO", "CTO", "Diretor de Inovação")
- "empresa": Apenas o nome da empresa (ex: "Microsoft", "NOS", "Farfetch")

TECNOLOGIAS MENCIONADAS:
- Apenas AI/ML + tecnologias de inovação + termos de negócio relevantes
- EXCLUIR: emails, telemóveis, URLs, informações de contacto, tecnologias genéricas (email, telefone, website)
- INCLUIR: machine learning, computer vision, LLMs, cloud, data analytics, automação, transformação digital, IA generativa

OUTREACH:
- Formato: 3-5 bullet points, cada um começando com "•"
- Extrair pontos de gancho para email comercial baseados em: desafios que AI pode resolver, oportunidades de AI, menção de orçamento/parcerias, urgência de projetos, interesse em inovação

Responde APENAS com um array JSON válido, sem texto adicional. Cada elemento do array deve ter exatamente estes campos:

[
  {
    "nome": "Nome completo da pessoa",
    "cargo": "Cargo/apenas título (sem empresa)",
    "empresa": "Nome da empresa (apenas)",
    "usa_ia": "Sim/Não - informação extra sobre isto",
    "vai_usar_ia": "Sim/Não - informação extra sobre isto",
    "departamento_ai": "Sim/Não - (externo se aplicável) + o que faz resumido",
    "pessoas_departamento_ai": "Nomes e empresa exterior se aplicável, ou vazio",
    "visao_estrategica": "Estratégia e inovação de curto e longo prazo agregadas",
    "tecnologias_mencionadas": ["lista", "de", "tecnologias", "AI", "cloud", "automação"],
    "principais_desafios": "Desafios principais",
    "outreach": "• Ponto 1\\n• Ponto 2\\n• Ponto 3 (máximo 5 bullets)",
    "potencial_cliente": "N/10 (Quente/Morno/Frio) - justificação breve do potencial como cliente para AI"
  }
]

Cada pessoa deve ter TODOS os campos preenchidos de forma independente.
Para o potencial_cliente, avalia considerando: se já usa AI (pode querer mais), se quer usar AI (oportunidade direta), se tem desafios que AI resolve, se mencionou orçamento ou parcerias tecnológicas.

Se algum campo não puder ser determinado, usa "Não mencionado".
Responde em Português."""


def build_prompt(transcript: str, metadata: dict) -> str:
    return f"""Analisa a seguinte entrevista de CEO.

Título do vídeo: {metadata.get('title', 'Desconhecido')}
Descrição: {metadata.get('description', 'Sem descrição')}

Transcrição:
{transcript}"""


def analyze_transcript(transcript: str, metadata: dict, api_key: str) -> list[dict] | None:
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
        parsed = json.loads(response_text)

        # Backward compatibility: wrap single dict in a list
        if isinstance(parsed, dict):
            parsed = [parsed]

        if not isinstance(parsed, list):
            return None

        # Cap at 5 persons maximum
        return parsed[:5]
    except (json.JSONDecodeError, IndexError, AttributeError):
        return None
