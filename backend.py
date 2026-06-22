import os
import re
import yaml
import asyncio
import dotenv
from typing import List, Dict, Any, Optional
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging
import traceback
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

from mcp.mcp_pubmed_client import get_mcp_client, shutdown_mcp_client
from core.agents import MultiAgentOrchestrator, _is_rate_limit_error


dotenv.load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY não definido no .env")

BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8001"))
PUBMED_SEARCH_LIMIT = int(os.getenv("PUBMED_SEARCH_LIMIT", "5"))
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "Templates_prompt", "prompt.yaml")

app = FastAPI(title="KlyraAI Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def on_shutdown():
    """Cleanup on server shutdown."""
    try:
        await shutdown_mcp_client()
    except Exception as e:
        import logging
        logging.error(f"Error during shutdown: {e}")



class ChatItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str
    history: List[ChatItem] = []
    limit: int = PUBMED_SEARCH_LIMIT


class ChatResponse(BaseModel):
    response: str
    references: str
    articles: List[dict]
    context: str


class AgentAnalysis(BaseModel):
    agent_name: str
    status: str
    output: str
    data: Dict[str, Any] = {}


class MultiAgentChatResponse(BaseModel):
    query: str
    final_response: str
    references: str
    articles: List[dict]
    context: str
    agent_analyses: Dict[str, AgentAnalysis]
    reasoning_path: str
    graph_nodes: List[Dict[str, Any]] = []
    graph_edges: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    clarifying_questions: List[str] = []
    memory_summary: Optional[str] = None


def model_call() -> ChatGroq:
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        api_key=GROQ_API_KEY,
    )


def load_system_prompt() -> str:
    if not os.path.exists(TEMPLATE_PATH):
        raise RuntimeError(f"Arquivo de prompt não encontrado: {TEMPLATE_PATH}")

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict) or "system_prompt" not in config:
        raise RuntimeError("O arquivo prompt.yaml deve conter a chave 'system_prompt'.")

    return config["system_prompt"]


def build_chat_history(history: List[ChatItem]) -> List:
    messages = []
    for item in history:
        content = item.content or ""
        role = item.role.lower()
        if role in ("assistant", "ai"):
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


async def extract_medical_term_with_llm(query: str, history: List[ChatItem] | None = None) -> str:
    if not query or not query.strip():
        return "medicine"

    try:
        # Quick heuristics: if the current query explicitly mentions a common disease term
        # or an uppercase acronym (e.g., 'AVC'), prefer that term and skip the LLM.
        q_raw = query or ""
        q = q_raw.lower()
        # explicit matches for common short forms and phrases
        if re.search(r"\b(avc|acidente vascular|stroke)\b", q):
            return "AVC"
        if re.search(r"\b(alzheimer|alzheimer's|demencia|demência|dementia)\b", q):
            return "Alzheimer"
        # detect uppercase acronyms like 'AVC' in the raw query
        m = re.search(r"\b([A-Z]{2,4})\b", q_raw)
        if m:
            return m.group(1)

        model = model_call()
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Você extrai termos médicos ou de saúde de mensagens. Responda APENAS com o termo ou expressão médica relevante para busca em base científica (doença, condição, síndrome, sintoma, tratamento, medicamento, etc.). Uma ou poucas palavras. Pode ser em português ou inglês. Sem explicação, sem aspas. Se a pergunta atual contiver um termo médico explícito (por exemplo 'AVC', 'acidente vascular', 'Alzheimer'), retorne esse termo. Use o histórico da conversa SOMENTE quando a pergunta for ambígua ou for um seguimento sem termo explícito (ex.: 'e prevenção?')."
            ),
            ("human", "{input}"),
        ])
        chain = prompt | model | StrOutputParser()

        history_text = ""
        if history:
            history_text = "\n".join(
                f"{item.role.capitalize()}: {item.content.strip()}"
                for item in history
                if item.content and item.content.strip()
            )

        input_text = query.strip()
        if history_text:
            input_text = (
                f"Histórico da conversa:\n{history_text}\n\n"
                f"Pergunta atual: {query.strip()}"
            )

        result = await chain.ainvoke({"input": input_text})
        term = (result or "").strip()
        term = term.strip('"\'.”').strip()
        if not term or len(term) > 200:
            return "medicine"
        return term
    except Exception:
        return "medicine"


def build_context_from_pubmed_articles(articles: List[dict]) -> str:
    if not articles:
        return ""
    parts = []
    for i, a in enumerate(articles, start=1):
        links_str = ""
        if a.get("full_text_links"):
            links_str = "\n  Links: " + "; ".join(
                f"{label}: {url}" for label, url in a["full_text_links"]
            )
        parts.append(
            f"[{i}] PMID: {a.get('pmid', '—')}  |  {a.get('journal', '—')}  ({a.get('year', '—')})\n"
            f"Título: {a.get('title', '—')}\n"
            f"DOI: {a.get('doi', '—')}\n"
            f"Autores: {a.get('authors', '—')}\n"
            f"Resumo: {a.get('abstract', '(sem resumo)')}{links_str}"
        )
    return "\n\n---\n\n".join(parts)


def build_references_markdown(articles: List[dict]) -> str:
    if not articles:
        return ""
    refs = []
    for a in articles:
        pmid = a.get("pmid") or "—"
        links = a.get("full_text_links") or []
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
    if not text or not text.strip():
        return text
    lines = text.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^Referências:\s*", stripped, re.IGNORECASE) and (
            "](http" not in line and "](https" not in line
        ):
            if re.search(r"PMID\s*\d+|\d{6,}", stripped):
                continue
        out.append(line)
    return "\n".join(out).strip()


async def search_pubmed_context(query: str, limit: int = 5) -> tuple[str, List[dict]]:
    term = (query or "").strip() or "medicine"
    try:
        client = await get_mcp_client()
        xml_text, articles = await client.search_and_parse(term, limit=limit)
        if not articles:
            return "", []
        return build_context_from_pubmed_articles(articles), articles
    except Exception as e:
        import logging
        logging.error(f"Error in search_pubmed_context: {e}")
        return "", []


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    context, articles = await search_pubmed_context(
        await extract_medical_term_with_llm(request.query),
        max(1, min(request.limit, PUBMED_SEARCH_LIMIT)),
    )

    if not context:
        context = "Nenhum artigo relevante encontrado no PubMed para esta busca."

    system_prompt = load_system_prompt()
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"{system_prompt}\n\nContexto:\n{{context}}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    chain = prompt | model_call() | StrOutputParser()

    try:
        response_text = await chain.ainvoke(
            {
                "input": request.query,
                "chat_history": build_chat_history(request.history),
                "context": context,
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    response_text = _strip_plain_references(response_text)
    references = build_references_markdown(articles)
    if references:
        response_text = response_text.rstrip() + "\n\n---\n\n" + references

    return ChatResponse(
        response=response_text,
        references=references,
        articles=articles,
        context=context,
    )


@app.post("/api/chat/multi-agent", response_model=MultiAgentChatResponse)
async def chat_multi_agent(request: ChatRequest):
    """
    Multi-agent reasoning endpoint.
    Executes 4 specialized agents for comprehensive analysis:
    1. Search & Selection
    2. Quality Analysis
    3. Insight Extraction
    4. Validation
    """
    # Get PubMed context
    search_term = await extract_medical_term_with_llm(request.query, request.history)
    context, articles = await search_pubmed_context(search_term, max(1, min(request.limit, PUBMED_SEARCH_LIMIT)))

    if not context:
        context = "Nenhum artigo relevante encontrado no PubMed para esta busca."

    # Execute multi-agent orchestration with error capture
    orchestrator = MultiAgentOrchestrator()
    try:
        agent_results = await orchestrator.execute(
            query=request.query,
            articles=articles,
            context=context,
            chat_history=build_chat_history(request.history)
        )
    except Exception as e:
        if _is_rate_limit_error(e):
            logging.warning("Groq rate limit reached during multi-agent execution: %s", e)
            raise HTTPException(
                status_code=429,
                detail=(
                    "Limite diário de tokens da Groq atingido para este modelo. "
                    "Aguarde a renovação do limite, altere GROQ_MODEL no .env "
                    "(ex.: llama-3.1-8b-instant) ou faça upgrade em "
                    "https://console.groq.com/settings/billing"
                ),
            )

        tb = traceback.format_exc()
        logging.exception("Error during multi-agent execution: %s", e)
        if os.getenv("BACKEND_VERBOSE", "1").lower() in ("1", "true", "yes"):
            return JSONResponse(status_code=500, content={"error": str(e), "traceback": tb})
        raise HTTPException(status_code=500, detail="Internal server error")

    # Build response
    final_response = agent_results["final_response"]
    rate_limited_agents = [
        r.agent_name
        for r in agent_results.get("agents", {}).values()
        if r.status == "error" and _is_rate_limit_error(Exception(r.data.get("error", r.output)))
    ]
    if rate_limited_agents:
        final_response = (
            "⚠️ **Limite de tokens da Groq atingido** — resposta parcial com base nos agentes que concluíram.\n\n"
            + final_response
        )
    references = build_references_markdown(articles)
    if references:
        final_response = final_response.rstrip() + "\n\n---\n\n" + references

    # Format agent analyses
    agent_analyses = {}
    for agent_key, result in agent_results.get("agents", {}).items():
        agent_analyses[agent_key] = AgentAnalysis(
            agent_name=result.agent_name,
            status=result.status,
            output=result.output,
            data=result.data or {}
        )

    # Create reasoning path summary
    reasoning_path = "\n".join([
        f"→ {result.agent_name}: {result.status.upper()}"
        for result in agent_results.get("agents", {}).values()
    ])

    return MultiAgentChatResponse(
        query=request.query,
        final_response=final_response,
        references=references,
        articles=articles,
        context=context,
        agent_analyses=agent_analyses,
        reasoning_path=reasoning_path,
        graph_nodes=agent_results.get("graph_nodes", []),
        graph_edges=agent_results.get("graph_edges", []),
        recommendations=agent_results.get("recommendations", []),
        clarifying_questions=agent_results.get("clarifying_questions", []),
        memory_summary=agent_results.get("memory_summary", "")
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)
