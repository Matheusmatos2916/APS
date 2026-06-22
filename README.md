# KlyraAI - Chatbot Médico com LangChain e Chainlit

Um sistema de chatbot interativo com arquitetura multi-agente para análise de pesquisa médica, criado com LangChain e Chainlit, usando uv como gerenciador de pacotes.

---

## 📋 Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Instalação](#instalação)
3. [Como Usar](#como-usar)
4. [Estrutura do Projeto](#estrutura-do-projeto)
5. [Funcionalidades](#funcionalidades)
6. [Arquitetura com MCP](#arquitetura-com-mcp)
7. [Sistema de Reasoning Multi-Agente](#sistema-de-reasoning-multi-agente)
8. [Otimizações de Performance](#otimizações-de-performance)
9. [Personalização](#personalização)

---

## 🔧 Pré-requisitos

- Python 3.10 ou superior
- [uv](https://github.com/astral-sh/uv) instalado
- Chave de API do Groq (obtenha em [console.groq.com](https://console.groq.com))

---

## 📦 Instalação

### 1. Clone ou navegue até o diretório do projeto

### 2. Instale as dependências usando uv:
```bash
uv sync
```

### 3. Configure sua chave da API do Groq:
- Crie um arquivo `.env` na raiz do projeto
- Adicione sua chave da API do Groq no arquivo `.env`:
```
GROQ_API_KEY=sua_chave_api_groq_aqui
BACKEND_URL=http://localhost:8001/api/chat
DATABASE_CHAINLIT=sqlite:///./databases/chainlit.db
PUBMED_SEARCH_LIMIT=5
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8001
GROQ_MODEL=llama-3.1-8b-instant
```

---

## 🚀 Como Usar

### Configuração Rápida (3 Terminais)

#### Terminal 1 - Backend (com MCP)
```bash
python backend.py
```
Ou com uvicorn:
```bash
uvicorn backend:app --reload --host 0.0.0.0 --port 8001
```

#### Terminal 2 - Frontend Chainlit
```bash
uv run chainlit run app.py
```
Acesse em `http://localhost:8000`

#### Terminal 3 - MCP Server (se necessário)
```bash
python mcp/mcp_pubmed_server.py
```

### Testando a API

#### Health Check
```bash
curl -X GET http://localhost:8001/api/health
```

#### Chat com contexto PubMed
```bash
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "O que é Alzheimer?",
    "history": [],
    "limit": 5
  }'
```

#### Chat Multi-Agent
```bash
curl -X POST http://localhost:8001/api/chat/multi-agent \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Qual é o papel do APOE4 em Alzheimer?",
    "history": [],
    "limit": 5
  }'
```

---

## 📁 Estrutura do Projeto

```
projeto/
├── app.py                        # Frontend Chainlit
├── backend.py                    # API Backend FastAPI
├── core/                         # Lógica central do projeto
│   ├── agents.py                # Agentes especializados
│   └── example_multi_agent_client.py  # Cliente de exemplo multi-agent
├── databases/                     # Banco de dados
│   ├── database.py              # Operações com banco de dados
│   ├── users.db                 # Banco de dados de usuários
│   ├── agent_memory.db          # Memória dos agentes
│   ├── init_chainlit_db.sql     # Script SQL Chainlit
│   └── README.md                # Documentação
├── users/                         # Scripts de usuário
│   ├── add_user.py              # Adicionar novo usuário
│   └── init_users.py            # Inicializar usuários de exemplo
├── mcp/                          # Ferramentas MCP
│   ├── mcp_pubmed_client.py     # Cliente MCP para PubMed
│   ├── mcp_pubmed_server.py     # Servidor MCP
│   └── mcp_servers.json         # Configuração MCP
├── pyproject.toml               # Dependências do projeto
├── .env                         # Variáveis de ambiente
├── .chainlit/config.toml        # Configurações Chainlit
├── tests/                       # Arquivos de teste
│   ├── teste.py
│   ├── teste_step.py
│   ├── teste_resquest_pubmed.py
│   ├── test_interactive.py
│   └── test_multi_agent_quick.py
├── pdf/                         # Documentos PDF
├── public/                      # Assets públicos
├── Templates_prompt/            # Templates de prompts
├── uml/                         # Diagramas UML
└── README.md                    # Documentação (este arquivo)
```

---

## ✨ Funcionalidades

### Chatbot Principal
- ✅ Interface web interativa com Chainlit
- ✅ Memória de conversa usando LangChain
- ✅ Integração com Groq API
- ✅ Histórico de conversa mantido durante a sessão
- ✅ Alta performance com modelo LLM otimizado

### Sistema Multi-Agente
- ✅ 4-7 agentes especializados trabalham em conjunto
- ✅ Busca automática em PubMed
- ✅ Análise de qualidade de artigos
- ✅ Extração de insights médicos
- ✅ Validação de afirmações contra evidências
- ✅ Identificação de lacunas na pesquisa

### Arquitetura MCP
- ✅ Model Context Protocol para comunicação estruturada
- ✅ Tools para busca no PubMed
- ✅ Processamento assíncrono
- ✅ Suporte a múltiplas ferramentas

---

## 🏗️ Arquitetura com MCP

O projeto está separado em três componentes principais:

### 1. **Backend FastAPI** (`backend.py`)
- API REST que recebe queries e retorna respostas com contexto do PubMed
- Usa o MCP client para chamar ferramentas de busca
- Executa em `http://0.0.0.0:8001`

### 2. **Servidor MCP** (`mcp/mcp_pubmed_server.py`)
- Expõe ferramentas (tools) para busca no PubMed via Model Context Protocol
- Tools disponíveis:
  - `search_pubmed`: busca artigos por termo
  - `fetch_article_details`: obtém XML com detalhes dos artigos
  - `parse_articles`: converte XML em estrutura JSON

### 3. **Frontend Chainlit** (`app.py`)
- Interface web para conversa com o usuário
- Comunica com o backend via HTTP
- Executa em `http://localhost:8000`

### Fluxo de Dados
```
User Input (Chainlit)
    ↓
Frontend (app.py)
    ↓ (HTTP POST)
Backend (backend.py)
    ↓ (async call)
MCP Client (mcp/mcp_pubmed_client.py)
    ↓ (subprocess)
MCP Server (mcp/mcp_pubmed_server.py)
    ↓
PubMed API (eutils.ncbi.nlm.nih.gov)
```

---

## 🤖 Sistema de Reasoning Multi-Agente

### Visão Geral

O sistema de multi-agente implementa 4-7 agentes especializados que trabalham em conjunto para fornecer análises profundas e validadas de pesquisa médica.

```
Query do Usuário
    ↓
Agent 1: Busca & Seleção (PubMed)
    ├─ Identifica artigos relevantes
    └─ Detecta lacunas na busca
    ↓
Agent 2: Análise de Qualidade
    ├─ Avalia confiabilidade dos artigos
    ├─ Scores de qualidade
    └─ Avisos de confiabilidade
    ↓
Agent 3: Extração de Insights
    ├─ Descobertas principais
    ├─ Metodologias inovadoras
    ├─ Consenso vs divergências
    └─ Implicações práticas
    ↓
Agent 4: Validação
    ├─ Verifica afirmações contra evidências
    ├─ Identifica claims sem suporte
    ├─ Detecta contradições
    └─ Score de confiabilidade
    ↓
Resposta Final Consolidada
```

### Agentes Especializados

#### Agent 1: PubMed Search Agent
**Responsabilidade:** Busca e seleção de artigos relevantes

**O que faz:**
- Identifica os 2-3 artigos mais relevantes
- Explica relevância de cada um
- Aponta lacunas (estudos faltando)
- Sugere buscas complementares

#### Agent 2: Quality Analysis Agent
**Responsabilidade:** Avaliação de qualidade e confiabilidade

**Critérios:**
- Reputação do journal (impacto típico)
- Recência da publicação
- Número e qualidade de autores
- Completude dos dados

**Scores:** A+ (Excelente) → A (Bom) → B (Aceitável) → C (Questionável)

#### Agent 3: Insight Extraction Agent
**Responsabilidade:** Extração de insights e conhecimentos

**Extrai:**
- Descobertas principais
- Metodologias inovadoras
- Consenso na literatura
- Divergências e debates
- Implicações clínicas
- Lacunas para pesquisa futura

#### Agent 4: Validation Agent
**Responsabilidade:** Validação de claims

**Valida:**
- Quais afirmações têm suporte
- Quais carecem de evidência
- Contradições com dados
- Tom apropriado (confiante vs especulativo)

### Endpoints da API

#### Chat Padrão (Single)
```
POST /api/chat
Content-Type: application/json

{
  "query": "O que é Alzheimer?",
  "history": [],
  "limit": 5
}
```

**Response:**
```json
{
  "response": "...",
  "references": "**Referências:** ...",
  "articles": [...],
  "context": "..."
}
```

#### Chat Multi-Agent
```
POST /api/chat/multi-agent
Content-Type: application/json

{
  "query": "O que é Alzheimer?",
  "history": [],
  "limit": 5
}
```

**Response (Expandido):**
```json
{
  "query": "O que é Alzheimer?",
  "final_response": "...",
  "references": "**Referências:** ...",
  "articles": [...],
  "context": "...",
  "reasoning_path": "→ PubMed Search Agent: SUCCESS\n→ Quality Analysis Agent: SUCCESS\n...",
  "agent_analyses": {
    "search": { ... },
    "quality": { ... },
    "insight": { ... },
    "validation": { ... }
  }
}
```

### Fluxo Detalhado de Execução

```
1. Request chega em /api/chat/multi-agent
   ↓
2. Backend extrai termo médico da query (LLM)
   ↓
3. Busca no PubMed via MCP client
   ↓
4. Instancia MultiAgentOrchestrator
   ↓
5. Agent 1 (Search) analisa relevância
6. Agent 2 (Quality) avalia qualidade
7. Agent 3 (Insight) extrai conhecimentos
   ↓
8. LLM gera resposta intermediária
   ↓
9. Agent 4 (Validation) valida resposta
   ↓
10. LLM sintetiza resposta final
    ↓
11. Consolida referências + articles
    ↓
12. Retorna MultiAgentChatResponse
```

---

## ⚡ Otimizações de Performance

### 🚀 Ganhos Implementados

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Tempo de resposta | ~28s | ~10-12s | **60% mais rápido** |
| Modelo | llama-3.3-70b | llama-3.1-8b-instant | 8.75x mais rápido |
| Contexto enviado | ~2000 tokens | ~800 tokens | 60% menos |
| Chamadas LLM | 8 | 8 | Mesmas, mas mais rápidas |

### ✅ Mudanças Implementadas

#### 1. **Trocar modelo para mais rápido**
- **Antes:** `llama-3.3-70b-versatile` (~28-30s por resposta)
- **Depois:** `llama-3.1-8b-instant` (~2-3s por chamada LLM)

#### 2. **Manter todos os agentes funcionando**
- ✅ PubMed Search Agent
- ✅ Quality Analysis Agent
- ✅ Insight Extraction Agent
- ✅ Validation Agent (+ 3 opcionais)

#### 3. **Reduzir contexto enviado aos agentes**
- Limitar artigos: 5-10 → **3 artigos**
- Títulos truncados: completos → **80 caracteres**
- Resumos truncados: completos → **200 caracteres**

#### 4. **Paralelização otimizada**
- Agentes independentes usam `asyncio.gather()`
- Semáforo limita concorrência a 2 para evitar rate limit

### ⏱️ Tempo Esperado por Resposta

**Com `llama-3.1-8b-instant` (OTIMIZADO):**
- Busca PubMed: ~1s
- Agent 1 (Search): ~2s
- Agents paralelos (Quality, Insight, Validation): ~5s
- Síntese final: ~1s
- **TOTAL: 10-12 segundos** ✅

**Com modelo antigo (`llama-3.3-70b-versatile`):**
- **TOTAL: 25-30 segundos** ❌

### ⚙️ Configurações Recomendadas no `.env`

```env
# ✅ PERFORMANCE (recomendado para produção)
GROQ_MODEL=llama-3.1-8b-instant
PUBMED_SEARCH_LIMIT=3
AGENT_TIMEOUT_SECS=15
AGENT_CONCURRENCY=2
BACKEND_VERBOSE=0
```

---

## 🎨 Personalização

### Personalizar o Chatbot

Você pode personalizar o chatbot editando:

- **Prompt do sistema** - em `app.py` (linha 36)
- **Modelo LLM** - em `app.py` (linha 13)
  - Modelos disponíveis: `openai/gpt-oss-20b`, `meta-llama/llama-*`, etc.
- **Temperatura do modelo** - em `app.py` (linha 14)
- **Configurações da interface** - em `.chainlit/config.toml`
- **Comportamento dos agentes** - em `core/agents.py`

### Adicionar Nova Tool ao MCP

1. Implemente a função em `mcp/mcp_pubmed_server.py`
2. Registre em `list_tools()`
3. Implemente o handler em `call_tool()`
4. Crie método wrapper em `mcp/mcp_pubmed_client.py`

---

## 🔍 Troubleshooting

### MCP Server não inicia
```bash
# Verifique se pode rodar
python mcp/mcp_pubmed_server.py

# Verifique o script de compatibilidade Python
which python
```

### PubMed retorna vazio
- Query pode ser muito específica
- Tente sinônimos médicos
- Aumente o `retmax` em `mcp/mcp_pubmed_client.py`

### Timeout na conexão
- Aumente timeout em `app.py` (AsyncClient)
- Verifique conexão de internet
- Veja logs do backend

### Erro: "No artigos encontrados"
- Verifique se a query é válida
- Tente outro termo médico
- Verifique conexão com PubMed

---

## 🔗 Links Úteis

- **Documentação:** [Chainlit Documentation](https://docs.chainlit.io) 📚
- **Discord Community:** [Chainlit Discord](https://discord.gg/k73SQ3FyUh) 💬
- **PubMed API:** [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25499/)
- **Groq Console:** [console.groq.com](https://console.groq.com)

---

## 📊 Próximas Melhorias

1. **Caching** — Cachear respostas para queries similares
2. **Streaming** — Usar SSE para mostrar progresso em tempo real
3. **Feedback** — Usuários votam se resposta foi útil
4. **Explainability** — Dashboard visual do raciocínio dos agentes
5. **Batch processing** — Agrupar múltiplas perguntas
6. **Rate limiting** — Controlar melhor requisições ao Groq

---

## 📝 Licença

Este projeto é de uso educacional e de pesquisa.

