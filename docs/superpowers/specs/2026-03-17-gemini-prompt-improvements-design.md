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
- `cargo` e `empresa` devem ter mais de 2 caracteres e não serem "Não mencionado"
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
- Responsabilidade: **Gemini deve filtrar** na resposta (não é validação Python)
- Apenas AI/ML + tecnologias de inovação + termos de negócio relevantes
- **Excluir**: emails, telemóveis, URLs, informações de contacto
- **Excluir**: tecnologias genéricas sem contexto (ex: "email", "telefone", "website")
- **Incluir**: machine learning, computer vision, LLMs, cloud, data analytics, automação, transformação digital, IA generativa, etc.

**Departamento AI:**
- Identificar se a empresa tem departamento AI
- Se sim, descrever resumidamente o que faz
- Indicar se é externo: "Sim (externo)" ou "Sim (interno)"
- Se externo, listar na coluna "Pessoas Associadas" os nomes e empresa

**Outreach:**
- Formato: **3-5 bullet points** concisos
- Extrair pontos de gancho para email comercial
- Baseado em:
  - Desafios mencionados que AI pode resolver
  - Oportunidades de AI identificadas
  - Menção de orçamento/parcerias tecnológicas
  - Urgência ou timeline de projetos
  - Interesse em inovação/transformação digital
- Exemplo: "• Desafio com processamento de dados em tempo real\n• Interesse em IA generativa para atendimento ao cliente"

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
    # Nome não pode ser "Não mencionado" ou vazio
    nome = person.get("nome", "").strip().lower()
    if nome in ["não mencionado", "nao mencionado", ""] or len(person.get("nome", "")) < 3:
        return False

    # Cargo e Empresa devem ter mais de 2 caracteres
    if len(person.get("cargo", "")) <= 2 or len(person.get("empresa", "")) <= 2:
        return False

    # Contar campos "não mencionado" (excluindo tecnologias que é lista)
    nao_mentionados = 0
    for k, v in person.items():
        if k == "tecnologias_mencionadas":
            continue  # Skip list field
        if isinstance(v, str) and v.strip().lower() in ["não mencionado", "nao mencionado", ""]:
            nao_mentionados += 1

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
# Defaults vazios se Gemini não retornar o campo
properties["Nome da Empresa"] = _rich_text(analysis.get("empresa") or "Não mencionado")
properties["Tem Departamento AI"] = _rich_text(analysis.get("departamento_ai") or "Não mencionado")
properties["Pessoas Departamento AI"] = _rich_text(analysis.get("pessoas_departamento_ai") or "")
properties["Visão Estratégica"] = _rich_text(analysis.get("visao_estrategica") or "Não mencionado")
properties["Outreach"] = _rich_text(analysis.get("outreach") or "")
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

**SCHEMA (para referência, usado em `create_database()`):**
- `SCHEMA` em `notion_db.py` precisa ser atualizado
- Remover: `Estratégia Digital`, `Inovação`, `Resumo Estratégico`
- Adicionar: `Nome da Empresa`, `Tem Departamento AI`, `Pessoas Departamento AI`, `Visão Estratégica`, `Outreach`

**Nota:** Novas databases criadas com código atualizado terão o schema correto. Databases existentes não são afetados pelo `SCHEMA` (são usadas como estão).

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

**Coexistência:**
- Código atualizado pode processar novos vídeos com novo schema
- Dados antigos permanecem no Notion com estrutura antiga
- Não há conflito - cada linha é independente

## Testes

### Testes Unitários (`tests/test_analyzer.py`)

**Atualizar testes existentes:**
- `test_analyze_transcript_returns_structured_data`: Mudar de `result["nome"]` para `result[0]["nome"]` (acesso à lista)
- Adicionar teste com múltiplas pessoas: mock retornando array JSON

**Novos casos de teste:**
1. `test_excludes_person_without_name`: Pessoa com nome "Não mencionado" ou vazio → retorna lista vazia
2. `test_excludes_person_with_too_many_empty_fields`: Pessoa com >3 campos "Não mencionado" → excluída
3. `test_excludes_person_with_short_cargo_empresa`: Pessoa com cargo/empresa <= 2 caracteres → excluída
4. `test_includes_valid_person`: Pessoa com todos campos válidos → incluída
5. `test_max_5_persons_returned`: Gemini retorna 7 pessoas → código retorna apenas 5
6. `test_outreach_format`: Outreach contém múltiplas linhas (bullets) não vazio
7. `test_cargo_empresa_separated`: `cargo` e `empresa` são campos separados no JSON retornado

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

**Aviso sobre schema do Notion:**
- Após criar as novas colunas no Notion, o código antigo não funcionará
- Se precisar de voltar ao código antigo, deve também remover as colunas novas manualmente
- Recomenda-se fazer backup do Notion antes de criar/alterar colunas

## Próximos Passos

Após aprovação deste design:
1. Criar plano de implementação detalhado (writing-plans)
2. Implementar alterações código
3. Atualizar testes
4. Testar manualmente via Streamlit
5. Documentar no README (instruções para criar colunas Notion)
