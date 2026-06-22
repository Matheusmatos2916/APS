import os
import re
import dotenv
import httpx
import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict

from databases.database import init_db, verify_user

dotenv.load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001/api/chat/multi-agent")
url_database = os.getenv("DATABASE_CHAINLIT")


@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    await init_db()
    if await verify_user(username, password):
        return cl.User(identifier=username)
    return None


@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(conninfo=url_database)


@cl.on_chat_start
async def start():
    cl.user_session.set("chat_history", [])
    await cl.Message(
        content=(
            "Bem-vindo ao **KlyraAI**. Digite sua pergunta médica e o sistema irá buscar resultados científicos."
        )
    ).send()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    history = []
    for step in thread.get("steps", []):
        if step["type"] == "user_message":
            history.append({"role": "user", "content": step.get("output", "")})
        elif step["type"] == "assistant_message":
            history.append({"role": "assistant", "content": step.get("output", "")})
    cl.user_session.set("chat_history", history)


@cl.on_message
async def main(message: cl.Message):
    history = cl.user_session.get("chat_history") or []
    payload = {
        "query": message.content,
        "history": history,
        "limit": int(os.getenv("PUBMED_SEARCH_LIMIT", "5")),
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(BACKEND_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    # Build assistant text with enriched sections
    ai_text = data.get("final_response") or data.get("response") or "Desculpe, não obtive resposta do backend."

    # Remove possíveis blocos de detalhes ou seções extras que já serão mostradas como componentes clicáveis
    def _strip_extra_sections(text: str, recommendations=None, clarifying=None, node_summary=None, edge_summary=None) -> str:
        if not text:
            return text
        # remove HTML <details> blocks
        text = re.sub(r"<details.*?>.*?</details>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # remove bolded Recommendations / Perguntas sections
        text = re.sub(r"\*\*Recomendações:\*\*.*?(?=\n\n|$)", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"\*\*Perguntas de follow-up:\*\*.*?(?=\n\n|$)", "", text, flags=re.DOTALL | re.IGNORECASE)
        # remove plain 'Recomendações:' or 'Perguntas de follow-up:' headings
        text = re.sub(r"Recomendações:.*?(?=\n\n|$)", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"Perguntas de follow-up:.*?(?=\n\n|$)", "", text, flags=re.DOTALL | re.IGNORECASE)
        # remove exact recommendation lines to avoid duplicates
        if recommendations:
            for r in recommendations:
                # remove bullet or plain occurrences
                text = text.replace(r"- " + r, "")
                text = text.replace(r, "")
        # remove clarifying questions
        if clarifying:
            for q in clarifying:
                text = text.replace(q, "")
                text = text.replace("- " + q, "")
        # remove graph summaries if provided
        if node_summary:
            text = text.replace(node_summary, "")
        if edge_summary:
            text = text.replace(edge_summary, "")
        # collapse multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # build graph summaries to remove duplicates if present
    node_summary = None
    edge_summary = None
    if data.get("graph_nodes") or data.get("graph_edges"):
        nodes = data.get("graph_nodes", [])
        edges = data.get("graph_edges", [])
        node_summary = "\n".join(
            f"- {node.get('type', 'unknown')}: {node.get('label', node.get('id', ''))}"
            for node in nodes[:10]
        ) or "(nenhum nó extraído)"
        edge_summary = "\n".join(
            f"- {edge.get('source')} → {edge.get('target')} ({edge.get('relation', 'relacionado_a')})"
            for edge in edges[:10]
        ) or "(nenhuma aresta extraída)"

    ai_text = _strip_extra_sections(
        ai_text,
        recommendations=data.get("recommendations", []),
        clarifying=data.get("clarifying_questions", []),
        node_summary=node_summary,
        edge_summary=edge_summary,
    )

    history.append({"role": "user", "content": message.content})
    history.append({"role": "assistant", "content": ai_text})
    cl.user_session.set("chat_history", history)

    await cl.Message(content=ai_text).send()

    # Usar componentes clicáveis do Chainlit para seções expansíveis
    if data.get("recommendations"):
        recommendations_md = "\n".join(f"- {item}" for item in data["recommendations"])
        async with cl.Step(name="Recomendações") as step:
            # Bind the output so the Step is shown with this content
            step.output = recommendations_md

    if data.get("clarifying_questions"):
        questions_md = "\n".join(f"- {q}" for q in data["clarifying_questions"])
        async with cl.Step(name="Perguntas de follow-up") as step:
            step.output = questions_md

    if data.get("graph_nodes") or data.get("graph_edges"):
        nodes = data.get("graph_nodes", [])
        edges = data.get("graph_edges", [])
        node_summary = "\n".join(
            f"- {node.get('type', 'unknown')}: {node.get('label', node.get('id', ''))}"
            for node in nodes[:10]
        ) or "(nenhum nó extraído)"
        edge_summary = "\n".join(
            f"- {edge.get('source')} → {edge.get('target')} ({edge.get('relation', 'relacionado_a')})"
            for edge in edges[:10]
        ) or "(nenhuma aresta extraída)"

        async with cl.Step(name="Grafo de conhecimento") as step:
            step.output = f"**Nós:**\n{node_summary}\n\n**Relações:**\n{edge_summary}"
