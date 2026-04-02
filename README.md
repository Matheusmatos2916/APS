# Chatbot com LangChain e Chainlit

Um chatbot interativo criado com LangChain e Chainlit, usando uv como gerenciador de pacotes.

## Pré-requisitos

- Python 3.10 ou superior
- [uv](https://github.com/astral-sh/uv) instalado
- Chave de API do Groq (obtenha em [console.groq.com](https://console.groq.com))

## Instalação

1. Clone ou navegue até o diretório do projeto

2. Instale as dependências usando uv:
```bash
uv sync
```

3. Configure sua chave da API do Groq:
   - Crie um arquivo `.env` na raiz do projeto
   - Adicione sua chave da API do Groq no arquivo `.env`:
   ```
   GROQ_API_KEY=sua_chave_api_groq_aqui
   ```

## Como usar

Execute o chatbot com o seguinte comando:

```bash
uv run chainlit run app.py
```

O chatbot estará disponível em `http://localhost:8000` no seu navegador.

## Estrutura do Projeto

- `app.py` - Código principal do chatbot com LangChain e Chainlit
- `pyproject.toml` - Configuração do projeto e dependências
- `.chainlit/config.toml` - Configurações da interface Chainlit
- `.env` - Variáveis de ambiente (não versionado)

## Funcionalidades

- Interface web interativa com Chainlit
- Memória de conversa usando LangChain
- Integração com Groq API usando o modelo `openai/gpt-oss-120b`
- Histórico de conversa mantido durante a sessão
- Alta performance com modelo GPT OSS 120B

## Personalização

Você pode personalizar o chatbot editando:
- O prompt do sistema em `app.py` (linha 36)
- O modelo LLM em `app.py` (linha 13) - outros modelos disponíveis: `openai/gpt-oss-20b`, `meta-llama/llama-*`, etc.
- A temperatura do modelo em `app.py` (linha 14)
- As configurações da interface em `.chainlit/config.toml`

