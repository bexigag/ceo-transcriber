# Design: Melhoria da Prompt do Gemini para Análise Estratégica

> Data: 2026-03-17
> Objetivo: Melhorar a qualidade da extração de informações da transcrição, focando em potenciais clientes para serviços de AI

## Contexto

O sistema atual analisa transcrições de vídeos de CEOs usando Gemini e cria linhas no Notion para cada pessoa identificada. O objetivo é encontrar potenciais clientes para a empresa que implementa AI ("We design AI strategy and build end-to-end solutions that scale your company").

## Problemas Identificados

1. **Pessoas sem relevância**: São adicionadas linhas onde o nome é "Não mencionado" ou com pouca informação
2. **Cargo duplica informação**: O campo "Cargo" contém tanto o cargo como a empresa
3. **Colunas redundantes**: "Estratégia Digital", "Inovação" e "Resumo Estratégico" têm conteúdo repetido
4. **Tecnologias irrelevantes**: A coluna inclui emails, telemóveis e outras informações não técnicas
5. **Falta informação AI**: Não há campos específicos sobre departamentos AI existentes
6. **Sem apoio comercial**: Não há pontos preparados para outreach/vendas

## Solução Proposta

### Nova Estrutura de Dados

**Campos retornados pelo Gemini (JSON):**

```json
[
  {
    "nome": "Nome completo",
    "cargo": "Cargo (sem empresa)",
    "empresa": "Nome da empresa",
    "usa_ia": "Sim/Não - informação extra",
    "vai_usar_ia": "Sim/Não - informação extra",
    "departamento_ai": "Sim/Não - (externo se aplicável) + o que faz resumido",
    "pessoas_departamento_ai": "Nomes e empresa exterior (se aplicável)",
    "visao_estrategica": "Estratégia/inovação curto e longo prazo agregadas",
    "tecnologias_mencionadas": ["AI", "cloud", "automação", "transformação digital", ...],
    "principais_desafios": "Desafios principais",
    "outreach": "Pontos-chave para abordagem comercial - desafios, oportunidades, mencionou orçamento/parcerias",
    "potencial_cliente": "N/10 (Quente/Morno/Frio) - justificação"
  }
]
```

### Regras do Gemini

**Novos filtros de inclusão:**
- Nome **não** pode ser "Não mencionado"
- Cargo e Empresa devem ser identificáveis
- Se mais de 3 campos estiverem "Não mencionado" → **excluir** a pessoa
- Excluir apresentadores/entrevistadores que apenas fazem perguntas
- Máximo 5 pessoas por vídeo

**Separação Cargo/Empresa:**
- `cargo`: Apenas o título/função (ex: "CEO", "CTO", "Diretor de Inovação")
- `empresa`: Nome da empresa (ex: "Microsoft", "NOS", "Farfetch")

**Visão Estratégica:**
- Combinar conteúdo de "Estratégia Digital" + "Inovação" + "Resumo Estratégico"
- Incluir visão de curto e longo prazo
- Focar em decisões, iniciativas e direção estratégica

**Tecnologias Mencionadas:**
- Apenas AI/ML + tecnologias de inovação + termos de negócio relevantes
- **Excluir**: emails, telemóveis, URLs, informações de contacto
- **Excluir**: tecnologias genéricas sem contexto (ex: "email", "telefone")
- **Incluir**: machine learning, computer vision, LLMs, cloud, data analytics, automação, transformação digital, etc.

**Departamento AI:**
- Identificar se a empresa tem departamento AI
- Se sim, descrever resumidamente o que faz
- Indicar se é externo: "Sim (externo)" ou "Sim (interno)"
- Se externo, listar na coluna "Pessoas Associadas" os nomes e empresa

**Outreach:**
- Extrair pontos de gancho para email comercial
- Baseado em:
  - Desafios mencionados que AI pode resolver
  - Oportunidades de AI identificadas
  - Menção de orçamento/parcerias tecnológicas
  - Urgência ou timeline de projetos
  - Interesse em inovação/transformação digital

## Alterações de Código

### `src/analyzer.py`

**Atualizar `SYSTEM_PROMPT`:**
- Nova estrutura de campos
- Novas regras de filtragem
- Instruções específicas para cada campo

**Validação no parsing:**
```python
# Após parse do JSON, validar cada pessoa:
def _is_person_valid(person: dict) -> bool:
    # Nome não pode ser "Não mencionado"
    if person.get("nome", "").strip().lower() in ["não mencionado", "nao mencionado", ""]:
        return False
    # Contar campos "não mencionado" (case insensitive)
    nao_mentionados = sum(
        1 for v in person.values()
        if isinstance(v, str) and v.strip().lower() in ["não mencionado", "nao mencionado", ""]
    )
    # Máximo 3 campos vazios
    return nao_mentionados <= 3
```

**Retorno:**
- Manter `list[dict] | None`
- Aplicar validação após o parse
- Retornar no máximo 5 pessoas válidas

### `src/notion_db.py`

**Novos campos no mapeamento `add_row()`:**
```python
properties["Nome da Empresa"] = _rich_text(analysis.get("empresa", ""))
properties["Tem Departamento AI"] = _rich_text(analysis.get("departamento_ai", ""))
properties["Pessoas Departamento AI"] = _rich_text(analysis.get("pessoas_departamento_ai", ""))
properties["Visão Estratégica"] = _rich_text(analysis.get("visao_estrategica", ""))
properties["Outreach"] = _rich_text(analysis.get("outreach", ""))
```

**Campo atualizado:**
```python
properties["Cargo"] = _rich_text(analysis.get("cargo", ""))  # Sem empresa
```

**Campos removidos do mapeamento:**
- `estrategia_digital`
- `inovacao`
- `resumo_estrategico`
(Substituídos por `visao_estrategica`)

**SCHEMA** (para referência, não é usado em runtime):
- Remover: `Estratégia Digital`, `Inovação`, `Resumo Estratégico`
- Adicionar: `Nome da Empresa`, `Tem Departamento AI`, `Pessoas Departamento AI`, `Visão Estratégica`, `Outreach`

### `streamlit_app.py` e `src/main.py`

**Sem alterações necessárias:**
- Ambos chamam `analyze_transcript()` e iteram sobre o resultado
- Não acedem diretamente aos campos, apenas passam para `add_row()`

## Colunas do Notion (Criação Manual)

O utilizador deve criar as seguintes colunas no Notion antes de usar o código atualizado:

1. **Nome** (title) - já existe
2. **Cargo** (rich_text) - já existe (vai sem empresa)
3. **Nome da Empresa** (rich_text) - **NOVA**
4. **Usa IA** (rich_text) - já existe
5. **Vai Usar IA** (rich_text) - já existe
6. **Tem Departamento AI** (rich_text) - **NOVA**
7. **Pessoas Departamento AI** (rich_text) - **NOVA**
8. **Visão Estratégica** (rich_text) - **NOVA** (substitui 3 colunas)
9. **Tecnologias Mencionadas** (multi_select) - já existe (filtro melhorado)
10. **Principais Desafios** (rich_text) - já existe
11. **Outreach** (rich_text) - **NOVA**
12. **Potencial Cliente** (rich_text) - já existe
13. **Link da Entrevista** (url) - já existe
14. **Data** (date) - já existe
15. **Status** (select) - já existe

**Colunas a remover manualmente (opcional):**
- Estratégia Digital
- Inovação
- Resumo Estratégico

## Migração de Dados

**Abordagem:**
- Dados existentes **não são migrados**
- Apenas **novos vídeos** usam a nova estrutura
- Vídeos já processados mantêm-se inalterados

**Justificativa:**
- Separação automática de cargo/empresa é propensa a erros
- Revisão manual seria necessária para garantir qualidade
- Focus em qualidade de dados novos vs. migração imperfeita

## Testes

### Testes Unitários (`tests/test_analyzer.py`)

**Novos casos de teste:**
1. Pessoa com nome "Não mencionado" → excluída
2. Pessoa com mais de 3 campos vazios → excluída
3. Pessoa válida → incluída
4. Tecnologias com email/telemóvel → filtradas
5. Parse de cargo/empresa separados
6. Outreach contém pontos comerciais relevantes

### Testes de Integração

**Manual (via Streamlit):**
1. Processar vídeo conhecido com 1 CEO válido
2. Processar vídeo com múltiplos entrevistados
3. Verificar que pessoas inválidas são excluídas
4. Verificar que colunas do Notion são preenchidas corretamente

## Rollback

Se necessário, é possível reverter:
- Git revert dos commits
- Restaurar `SYSTEM_PROMPT` anterior
- Restaurar mapeamento de campos em `notion_db.py`
- Dados já escritos no Notion permanecem (não são afetados)

## Próximos Passos

Após aprovação deste design:
1. Criar plano de implementação detalhado (writing-plans)
2. Implementar alterações código
3. Atualizar testes
4. Testar manualmente via Streamlit
5. Documentar no README (instruções para criar colunas Notion)
