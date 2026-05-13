from operator import itemgetter
import os
import re
import yaml
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
import subprocess
import threading
import requests
import asyncio
import dotenv
from typing import Dict, Optional, List
import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict
from database import init_db, verify_user
# --- Qdrant desativado: pesquisa feita via PubMed ---
# from qdrant_client import QdrantClient
# from sentence_transformers import SentenceTransformer
# from main import (
#     COLLECTION_NAME,
#     EMBEDDING_MODEL,
#     extract_pages,
#     parse_structure,
#     normalize_chunks,
#     init_qdrant,
#     upsert_chunks,
# )
from teste_resquest_pubmed import search_pubmed, fetch_article_details, parse_articles

dotenv.load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
chainlit_auth_secret = os.getenv("CHAINLIT_AUTH_SECRET")
url_database = os.getenv("DATABASE_CHAINLIT")


def _ensure_chainlit_sql_schema() -> None:
    """
    Garante colunas exigidas pela versão atual do Chainlit no PostgreSQL.
    Sem isso, INSERTs em `steps` falham (ex.: coluna autoCollapse ausente após upgrade)
    e o histórico não persiste — ver logs do Chainlit.
    """
    if not url_database or "postgresql" not in url_database:
        return
    dsn = url_database.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        import asyncpg
    except ImportError:
        return

    async def _migrate() -> None:
        conn = await asyncpg.connect(dsn=dsn)
        try:
            await conn.execute(
                'ALTER TABLE steps ADD COLUMN IF NOT EXISTS "autoCollapse" BOOLEAN DEFAULT FALSE'
            )
        finally:
            await conn.close()

    try:
        asyncio.run(_migrate())
    except RuntimeError:
        # Import do app com event loop já ativo (raro): migração manual ou script separado
        print(
            "[chainlit-db] Migração automática ignorada (event loop ativo). "
            'Execute no PostgreSQL: ALTER TABLE steps ADD COLUMN IF NOT EXISTS "autoCollapse" BOOLEAN DEFAULT FALSE;'
        )
    except Exception as e:
        print(
            f"[chainlit-db] Falha na migração automática: {e!r}. "
            'Se o histórico não salvar, rode: ALTER TABLE steps ADD COLUMN IF NOT EXISTS "autoCollapse" BOOLEAN DEFAULT FALSE;'
        )


_ensure_chainlit_sql_schema()

# --- Qdrant desativado ---
# PDF do ROD para indexar no Qdrant em memória
# PDF_PATH = os.path.join(os.path.dirname(__file__), "pdf", "ROD_atualizado.pdf")
# QDRANT_SEARCH_LIMIT = int(os.getenv("QDRANT_SEARCH_LIMIT", "5"))
# Qdrant em memória compartilhado no processo (construído na primeira mensagem, em thread)
# _global_qdrant_client: Optional[QdrantClient] = None
# _global_embedding_model: Optional[SentenceTransformer] = None
# _qdrant_build_lock = asyncio.Lock()

# Limite de artigos PubMed para contexto (equivalente ao QDRANT_SEARCH_LIMIT)
PUBMED_SEARCH_LIMIT = int(os.getenv("PUBMED_SEARCH_LIMIT", "5"))


async def extract_medical_term_with_llm(query: str) -> str:
    """
    Identifica o termo médico (ou de saúde) na mensagem do usuário utilizando apenas LLM.
    Retorna o termo para usar na busca no PubMed.
    """
    if not query or not query.strip():
        return "medicine"
    try:
        model = model_call()
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Você extrai termos médicos ou de saúde de mensagens. Responda APENAS com o termo ou expressão médica relevante para busca em base científica (doença, condição, síndrome, sintoma, tratamento, medicamento, etc.). Uma ou poucas palavras. Pode ser em português ou inglês. Sem explicação, sem aspas. Se não houver termo claramente médico, devolva a palavra ou expressão mais relevante da frase."),
            ("human", "{input}"),
        ])
        chain = prompt | model | StrOutputParser()
        result = await chain.ainvoke({"input": query.strip()})
        term = (result or "").strip()
        # Remove possíveis aspas ou pontos que o modelo tenha adicionado
        term = term.strip('"\'.”').strip()
        if not term or len(term) > 200:
            return "medicine"
        return term
    except Exception:
        return "medicine"


def model_call():
    """
    Retorna o modelo ChatGroq configurado para fazer requisições.
    
    Returns:
        ChatGroq: Instância do modelo configurado com a API key.
    """
    model = ChatGroq(
        model="openai/gpt-oss-120b",
        api_key=groq_api_key,
    )
    return model


# --- Funções Qdrant desativadas ---
# def build_in_memory_qdrant():
#     """
#     Cria cliente Qdrant em :memory:, indexa o PDF do ROD e retorna (client, embedding_model).
#     """
#     client = init_qdrant(host=":memory:")
#     pages = extract_pages(PDF_PATH)
#     raw_chunks = parse_structure(pages)
#     documents = normalize_chunks(raw_chunks)
#     embedding_model = SentenceTransformer(EMBEDDING_MODEL)
#     upsert_chunks(client, embedding_model, documents)
#     return client, embedding_model
#
#
# def search_qdrant(
#     client: QdrantClient,
#     embedding_model: SentenceTransformer,
#     query: str,
#     limit: int = 5,
# ) -> List[dict]:
#     """
#     Busca semântica no Qdrant. Retorna lista de payloads (text, artigo, titulo, etc.).
#     """
#     if not client or not embedding_model:
#         return []
#     query_vector = embedding_model.encode(query).tolist()
#     results = client.query_points(
#         collection_name=COLLECTION_NAME,
#         query=query_vector,
#         limit=limit,
#         with_payload=True,
#     )
#     out = []
#     for r in results.points:
#         payload = r.payload or {}
#         out.append(payload)
#     return out
#
#
# def build_context_from_results(results: List[dict]) -> str:
#     """Monta um único texto de contexto a partir dos resultados da busca no Qdrant."""
#     if not results:
#         return ""
#     parts = []
#     for i, payload in enumerate(results, start=1):
#         artigo = payload.get("artigo", "")
#         titulo = payload.get("titulo", "")
#         capitulo = payload.get("capitulo", "")
#         secao = payload.get("secao", "")
#         pagina = payload.get("pagina", "")
#         text = payload.get("text", "")
#         parts.append(
#             f"[{i}] {artigo}\n"
#             f"Título: {titulo}\nCapítulo: {capitulo}\nSeção: {secao}\nPágina: {pagina}\n\n{text.strip()}"
#         )
#     return "\n\n---\n\n".join(parts)


def search_pubmed_context(query: str, limit: int = 5) -> tuple:
    """
    Busca no PubMed com a query e monta texto de contexto + lista de artigos.
    Retorna (context_str, articles) para permitir montar a seção Referências com links.
    """
    term = (query or "").strip() or "medicine"
    try:
        ids = search_pubmed(term, retmax=max(limit, 10))

        print("\n" + "=" * 60)
        print(f"[PubMed] Termo de busca: \"{term}\"")

        if not ids:
            print("[PubMed] Nenhum ID retornado pela API (0 artigos).")
            print("=" * 60 + "\n")
            return ("", [])

        ids = ids[:limit]
        print(f"[PubMed] IDs retornados: {', '.join(ids)}")

        xml_text = fetch_article_details(ids)
        if not xml_text:
            print("[PubMed] Resposta XML vazia ao buscar detalhes dos artigos.")
            print("=" * 60 + "\n")
            return ("", [])

        articles = parse_articles(xml_text)
        print(f"[PubMed] {len(articles)} artigo(s) parseado(s) da resposta XML.")

        if not articles:
            print("[PubMed] Nenhum artigo válido após parse do XML.")
            print("=" * 60 + "\n")
            return ("", [])

        for i, a in enumerate(articles, start=1):
            print(f"  [{i}] PMID: {a.get('pmid', '—')}  |  {a.get('journal', '—')}  ({a.get('year', '—')})")
            print(f"      Título: {a.get('title', '—')}")
        print("=" * 60 + "\n")

        context_str = build_context_from_pubmed_articles(articles)
        return (context_str, articles)
    except Exception as e:
        print("\n[PubMed] Erro inesperado em search_pubmed_context:", repr(e))
        print("=" * 60 + "\n")
        return ("", [])


def build_context_from_pubmed_articles(articles: List[dict]) -> str:
    """Monta um único texto de contexto a partir dos artigos retornados pelo PubMed."""
    if not articles:
        return ""
    parts = []
    for i, a in enumerate(articles, start=1):
        links_str = ""
        if a.get("full_text_links"):
            links_str = "\n  Links: " + "; ".join(f"{label}: {url}" for label, url in a["full_text_links"])
        parts.append(
            f"[{i}] PMID: {a.get('pmid', '—')}  |  {a.get('journal', '—')}  ({a.get('year', '—')})\n"
            f"Título: {a.get('title', '—')}\n"
            f"DOI: {a.get('doi', '—')}\n"
            f"Autores: {a.get('authors', '—')}\n"
            f"Resumo: {a.get('abstract', '(sem resumo)')}{links_str}"
        )
    return "\n\n---\n\n".join(parts)


def build_references_markdown(articles: List[dict]) -> str:
    """
    Monta a seção Referências com links clicáveis (Markdown) usando full_text_links dos artigos.
    Ex: [PMID 41832772](https://pubmed.ncbi.nlm.nih.gov/41832772/); [PMID 41832727](...)
    """
    if not articles:
        return ""
    refs = []
    for a in articles:
        pmid = a.get("pmid") or "—"
        links = a.get("full_text_links") or []
        # Preferir link PubMed; senão o primeiro disponível
        url = None
        for label, u in links:
            if label == "PubMed" or "pubmed" in (label or "").lower():
                url = u
                break
        if not url and links:
            url = links[0][1]
        if url:
            refs.append(f"[PMID {pmid}]({url})")
        else:
            refs.append(f"PMID {pmid}")
    return "**Referências:** " + "; ".join(refs) + "."


def _strip_plain_references(text: str) -> str:
    """
    Remove do texto qualquer bloco 'Referências: PMID ...' em texto simples (sem links),
    para ficar só o bloco que adicionamos com links clicáveis (em rosa).
    """
    if not text or not text.strip():
        return text
    # Linhas com links clicáveis contêm "](http" (markdown). Remover só linhas que são "Referências: PMID ..." sem link.
    lines = text.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        # Pula linha que é só "Referências: PMID 123; 456; ..." (sem ] ou (http)
        if re.match(r"^Referências:\s*", stripped, re.IGNORECASE) and "](http" not in line and "](https" not in line:
            if re.search(r"PMID\s*\d+|\d{6,}", stripped):  # tem PMID ou números longos (IDs)
                continue  # não adiciona essa linha
        out.append(line)
    return "\n".join(out).strip()


@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    """
    Callback de autenticação que verifica as credenciais no banco de dados.
    
    Args:
        username: Nome de usuário
        password: Senha
        
    Returns:
        cl.User se as credenciais forem válidas, None caso contrário
    """
    # Garante que o banco de dados está inicializado
    await init_db()
    
    # Verifica as credenciais no banco de dados
    if await verify_user(username, password):
        return cl.User(identifier=username)
    else:
        return None

@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(conninfo=url_database)

def _setup_chain():
    """
    Modo demonstração (UI + histórico): não instancia LLM nem chain na sessão.
    Para reativar a resposta real da IA, descomente o bloco abaixo e comente as duas linhas de sessão.
    """
    cl.user_session.set("chat_history", [])
    cl.user_session.set("chain", None)
    # model = model_call()
    # cl.user_session.set("model", model)
    # cl.user_session.set("chat_history", [])
    # yaml_path = os.path.join(os.path.dirname(__file__), "Templates_prompt", "prompt.yaml")
    # with open(yaml_path, "r", encoding="utf-8") as f:
    #     prompt_config = yaml.safe_load(f)
    # system_prompt_base = prompt_config.get("system_prompt", "")
    # system_prompt = (
    #     f"{system_prompt_base}\n\n"
    #     "Use o contexto abaixo, que contém artigos científicos do PubMed, para fundamentar sua resposta. "
    #     "Quando houver artigos no contexto, cite-os na resposta (mencione PMID, título ou autores). "
    #     "Só diga que não encontrou artigos se o contexto estiver vazio ou indicar explicitamente que não há resultados. "
    #     "Não inclua no final da sua resposta uma seção 'Referências' nem lista de PMIDs; as referências com links serão adicionadas automaticamente.\n\n"
    #     "Contexto (artigos PubMed):\n{context}"
    # )
    # prompt = ChatPromptTemplate.from_messages([
    #     ("system", system_prompt),
    #     MessagesPlaceholder(variable_name="chat_history"),
    #     ("human", "{input}")
    # ])
    # chain = prompt | model | StrOutputParser()
    # cl.user_session.set("chain", chain)


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    _setup_chain()
    # Restaura histórico do thread (sobrescreve o [] de _setup_chain)
    cl.user_session.set("chat_history", [])

    history = []
    for message in thread['steps']:
        if message['type'] == 'user_message':
            history.append(HumanMessage(content=message['output']))
        elif message['type'] == 'assistant_message':
            history.append(AIMessage(content=message['output']))
    cl.user_session.set("chat_history", history)

@cl.on_chat_start
async def chat_start():
    _setup_chain()
    await cl.Message(
        content=(
            "Bem-vindo ao **KlyraAI**. Você está no modo demonstração: o layout e o envio de mensagens "
            "funcionam normalmente e o histórico da sessão é mantido, mas a resposta do assistente é **simulada** "
            "(sem chamadas à LLM nem ao PubMed)."
        )
    ).send()

# --- Qdrant desativado: não é mais necessário indexar ROD ---
# async def _ensure_qdrant_ready(msg_loading: Optional[cl.Message] = None):
#     """Garante que o Qdrant em memória está construído (roda em thread para não bloquear)."""
#     global _global_qdrant_client, _global_embedding_model
#     if _global_qdrant_client is not None:
#         return
#     async with _qdrant_build_lock:
#         if _global_qdrant_client is not None:
#             return
#         if msg_loading:
#             msg_loading.content = "Indexando o documento ROD, aguarde alguns instantes..."
#             await msg_loading.update()
#         _global_qdrant_client, _global_embedding_model = await asyncio.to_thread(build_in_memory_qdrant)


@cl.on_message
async def main(message: cl.Message):
    chat_history = cl.user_session.get("chat_history") or []

    msg = cl.Message(content="")
    await msg.send()

    # --- Modo demonstração: resposta mockada (sem LLM / sem PubMed). Histórico de HumanMessage/AIMessage mantido. ---
    user_text = (message.content or "").strip() or "(mensagem vazia)"
    chat_history.append(HumanMessage(content=message.content))
    response = (
        f"*(Resposta simulada do assistente)*\n\n"
        f"Recebi a sua mensagem: **{user_text}**\n\n"
        "Em produção, aqui entrariam a extração do termo com LLM, a busca no PubMed e a resposta gerada pelo modelo."
    )
    chat_history.append(AIMessage(content=response))
    cl.user_session.set("chat_history", chat_history)
    msg.content = response
    await msg.update()

    # --- Produção (LLM + PubMed): descomente para reativar ---
    # chain = cl.user_session.get("chain")
    # # Extrai termo médico com LLM (ex: "quero saber mais sobre alzheimer" -> "alzheimer")
    # search_term = await extract_medical_term_with_llm(message.content)
    # msg.content = "Buscando artigos no PubMed..."
    # await msg.update()
    # context, articles = await asyncio.to_thread(
    #     search_pubmed_context,
    #     search_term,
    #     limit=PUBMED_SEARCH_LIMIT,
    # )
    # if not context:
    #     context = "Nenhum artigo relevante encontrado no PubMed para esta busca."
    # chat_history.append(HumanMessage(content=message.content))
    # response = await chain.ainvoke({
    #     "input": message.content,
    #     "chat_history": chat_history,
    #     "context": context,
    # })
    # response = _strip_plain_references(response)
    # references_block = build_references_markdown(articles)
    # if references_block:
    #     response = response.rstrip() + "\n\n---\n\n" + references_block
    # chat_history.append(AIMessage(content=response))
    # cl.user_session.set("chat_history", chat_history)
    # msg.content = response
    # await msg.update()
