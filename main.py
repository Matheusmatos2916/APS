from operator import itemgetter
import os
import yaml
import re
import fitz
import asyncio
import dotenv
from uuid import uuid4
from typing import Dict, Optional, List

import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer

from databases.database import init_db, verify_user

dotenv.load_dotenv()

# =========================
# ENV
# =========================

groq_api_key = os.getenv("GROQ_API_KEY")
url_database = os.getenv("DATABASE_CHAINLIT")

PDF_PATH = os.path.join(os.path.dirname(__file__), "pdf", "ROD_atualizado.pdf")

COLLECTION_NAME = "rod_ifce"
EMBEDDING_MODEL = "jmbrito/ptbr-similarity-e5-small"
embedding_filter = SentenceTransformer(EMBEDDING_MODEL)
vector_size = embedding_filter.get_sentence_embedding_dimension()

QDRANT_SEARCH_LIMIT = 5


# =========================
# EXTRAÇÃO DO PDF
# =========================

def extract_pages(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        pages.append({
            "page": i + 1,
            "text": page.get_text()
        })
    return pages


# =========================
# PARSER HIERÁRQUICO
# =========================

TITLE_RE = re.compile(r"TÍTULO\s+[IVX]+.*")
CHAPTER_RE = re.compile(r"Capítulo\s+[IVX]+.*")
SECTION_RE = re.compile(r"(SEÇÃO|SUBSEÇÃO)\s+[IVX]+.*")
ARTICLE_RE = re.compile(r"Art\.\s*\d+º?")

def parse_structure(pages):

    current = {"titulo": None, "capitulo": None, "secao": None}
    chunks = []
    current_chunk = None

    for page in pages:
        for line in page["text"].split("\n"):

            line = line.strip()

            if TITLE_RE.match(line):
                current["titulo"] = line

            elif CHAPTER_RE.match(line):
                current["capitulo"] = line

            elif SECTION_RE.match(line):
                current["secao"] = line

            elif ARTICLE_RE.match(line):

                if current_chunk:
                    chunks.append(current_chunk)

                current_chunk = {
                    "text": line + "\n",
                    "pagina": page["page"],
                    "metadata": current.copy(),
                    "artigo": line
                }

            else:
                if current_chunk:
                    current_chunk["text"] += line + "\n"

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# =========================
# NORMALIZAÇÃO
# =========================

def normalize_chunks(raw_chunks):

    documents = []

    for c in raw_chunks:
        documents.append({
            "text": c["text"].strip(),
            "metadata": {
                "titulo": c["metadata"]["titulo"],
                "capitulo": c["metadata"]["capitulo"],
                "secao": c["metadata"]["secao"],
                "artigo": c["artigo"],
                "pagina": c["pagina"],
            }
        })

    return documents


# =========================
# QDRANT
# =========================

def init_qdrant(host=":memory:"):

    client = QdrantClient(":memory:")

    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE
        )
    )

    return client


def upsert_chunks(client, model, chunks):

    points = []

    for chunk in chunks:

        embedding = model.encode(chunk["text"]).tolist()

        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=embedding,
                payload={
                    "text": chunk["text"],
                    **chunk["metadata"]
                }
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )


# =========================
# BUSCA SEMÂNTICA
# =========================

def search_qdrant(client, model, query, limit=5):

    query_vector = model.encode(query).tolist()

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True
    )

    out = []

    for r in results.points:
        payload = r.payload or {}
        out.append(payload)

    return out


def build_context(results):

    if not results:
        return ""

    parts = []

    for r in results:

        parts.append(
            f"{r.get('artigo')}\n"
            f"Título: {r.get('titulo')}\n"
            f"Capítulo: {r.get('capitulo')}\n"
            f"Seção: {r.get('secao')}\n"
            f"Página: {r.get('pagina')}\n\n"
            f"{r.get('text')}"
        )

    return "\n\n---\n\n".join(parts)


# =========================
# MODEL
# =========================

def model_call():

    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=groq_api_key,
    )


# =========================
# RAG GLOBAL
# =========================

qdrant_client: Optional[QdrantClient] = None
embedding_model: Optional[SentenceTransformer] = None


async def build_rag():

    global qdrant_client, embedding_model

    qdrant_client = init_qdrant()

    pages = extract_pages(PDF_PATH)

    raw_chunks = parse_structure(pages)

    documents = normalize_chunks(raw_chunks)

    embedding_model = SentenceTransformer(EMBEDDING_MODEL)


    await asyncio.to_thread(
        upsert_chunks,
        qdrant_client,
        embedding_model,
        documents
    )


# =========================
# LOGIN
# =========================

@cl.password_auth_callback
async def auth_callback(username: str, password: str):

    await init_db()

    if await verify_user(username, password):
        return cl.User(identifier=username)

    return None


@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(conninfo=url_database)


# =========================
# CHAT START
# =========================

@cl.on_chat_start
async def start():

    await build_rag()

    model = model_call()

    cl.user_session.set("model", model)
    cl.user_session.set("chat_history", [])

    yaml_path = os.path.join(
        os.path.dirname(__file__),
        "Templates_prompt",
        "prompt.yaml"
    )

    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    system_prompt = config["system_prompt"]

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + "\n\nContexto:\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])

    chain = prompt | model | StrOutputParser()

    cl.user_session.set("chain", chain)


# =========================
# CHAT
# =========================

@cl.on_message
async def main(message: cl.Message):

    chain = cl.user_session.get("chain")
    history = cl.user_session.get("chat_history")

    msg = cl.Message(content="")
    await msg.send()

    results = search_qdrant(
        qdrant_client,
        embedding_model,
        message.content
    )

    context = build_context(results)

    history.append(HumanMessage(content=message.content))

    response = await chain.ainvoke({
        "input": message.content,
        "chat_history": history,
        "context": context
    })

    history.append(AIMessage(content=response))

    cl.user_session.set("chat_history", history)

    msg.content = response

    await msg.update()