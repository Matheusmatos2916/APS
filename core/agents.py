"""
Multi-Agent Reasoning System for Medical Research Analysis.
Coordinates 4 specialized agents for comprehensive article analysis.
"""

import asyncio
import json
import os
import time
from typing import List, Dict, Any
from dataclasses import dataclass
from groq import RateLimitError
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import logging

logger = logging.getLogger(__name__)
# Configure verbose logging for agents when AGENT_VERBOSE env var is set
if os.getenv("AGENT_VERBOSE", "1").lower() in ("1", "true", "yes"):
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        logger.addHandler(ch)


@dataclass
class AgentResult:
    """Result from an agent execution."""
    agent_name: str
    status: str  # "success" or "error"
    output: str
    data: Dict[str, Any] = None


def get_groq_model():
    """Get configured Groq model."""
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        api_key=os.getenv("GROQ_API_KEY"),
    )


def _is_rate_limit_error(exc: Exception) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    msg = str(exc).lower()
    return "rate_limit" in msg or "rate limit" in msg or "429" in msg


class PubMedSearchAgent:
    """Agent 1: Searches PubMed for relevant articles."""

    def __init__(self):
        self.model = get_groq_model()
        self.name = "PubMed Search Agent"

    async def execute(self, query: str, articles: List[dict]) -> AgentResult:
        """
        Analyze query and select the most relevant articles from search results.
        """
        if not articles:
            return AgentResult(
                agent_name=self.name,
                status="success",
                output="Nenhum artigo encontrado no PubMed.",
                data={"articles": [], "analysis": "Busca retornou vazio"}
            )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Você é um especialista em busca científica. Identifique os 2-3 artigos mais relevantes.
Formato: ARTIGOS RELEVANTES:
- [PMID]: Título - Por que relevante"""
            ),
            ("human", "{input}")
        ])

        chain = prompt | self.model | StrOutputParser()

        try:
            # Truncate article titles for faster processing
            articles_text = "\n".join([
                f"[{a['pmid']}] {a['title'][:100]} ({a['journal']}, {a['year']})"
                for a in articles[:3]
            ])

            result = await chain.ainvoke({
                "input": f"Pergunta: {query}\n\nArtigos:\n{articles_text}"
            })

            return AgentResult(
                agent_name=self.name,
                status="success",
                output=result,
                data={"total_articles_found": len(articles), "top_articles": articles[:3]}
            )
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return AgentResult(
                agent_name=self.name,
                status="error",
                output=f"Erro ao analisar artigos: {str(e)}",
                data={"error": str(e)}
            )


class QualityAnalysisAgent:
    """Agent 2: Analyzes quality and reliability of articles."""

    def __init__(self):
        self.model = get_groq_model()
        self.name = "Quality Analysis Agent"

    async def execute(self, articles: List[dict]) -> AgentResult:
        """
        Assess the quality, credibility, and reliability of articles.
        """
        if not articles:
            return AgentResult(
                agent_name=self.name,
                status="success",
                output="Nenhum artigo para analisar.",
                data={"quality_scores": []}
            )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Você é um revisor científico experiente. Avalie a qualidade de cada artigo baseado em:
1. Journal reputation (impact factor típico)
2. Ano de publicação (recência)
3. Número de autores (qualidade coletiva)
4. Presença de abstract/resumo (completude)

Escala: EXCELENTE (A+), BOM (A), ACEITÁVEL (B), QUESTIONÁVEL (C)

Formato:
ANÁLISE DE QUALIDADE:
- [PMID]: [JOURNAL] → Score: [SCORE]
  Justificativa: [razão]
  
ARTIGOS MAIS CONFIÁVEIS:
[Lista dos 3 melhores]

AVISOS DE CONFIABILIDADE:
[Se houver artigos com problemas]"""
            ),
            ("human", "{input}")
        ])

        chain = prompt | self.model | StrOutputParser()

        try:
            articles_text = "\n".join([
                f"[{a['pmid']}] {a['title'][:80]} ({a['journal']}, {a['year']})"
                for a in articles[:3]
            ])

            result = await chain.ainvoke({
                "input": f"Avalie:\n{articles_text}"
            })

            return AgentResult(
                agent_name=self.name,
                status="success",
                output=result,
                data={"articles_reviewed": len(articles)}
            )
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return AgentResult(
                agent_name=self.name,
                status="error",
                output=f"Erro ao analisar qualidade: {str(e)}",
                data={"error": str(e)}
            )


class InsightExtractionAgent:
    """Agent 3: Extracts key insights and findings from articles."""

    def __init__(self):
        self.model = get_groq_model()
        self.name = "Insight Extraction Agent"

    async def execute(self, query: str, articles: List[dict], context: str) -> AgentResult:
        """
        Extract key insights, findings, and patterns from articles.
        """
        if not articles:
            return AgentResult(
                agent_name=self.name,
                status="success",
                output="Nenhum artigo para extrair insights.",
                data={"insights": []}
            )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Você é um especialista em síntese de pesquisa. Extraia os insights-chave:
1. Descobertas principais
2. Metodologias inovadoras
3. Consenso vs divergências
4. Implicações práticas
5. Lacunas de conhecimento identificadas

Formato:
DESCOBERTAS PRINCIPAIS:
- [Insight 1]
- [Insight 2]

METODOLOGIAS INOVADORAS:
- [Método]

CONSENSO NA LITERATURA:
[O que a maioria dos estudos concorda]

DIVERGÊNCIAS E DEBATES:
[Onde ainda há desacordo]

IMPLICAÇÕES CLÍNICAS/PRÁTICAS:
[Como aplicar esse conhecimento]

LACUNAS PARA PESQUISA FUTURA:
- [Gap 1]"""
            ),
            ("human", "{input}")
        ])

        chain = prompt | self.model | StrOutputParser()

        try:
            articles_summary = "\n".join([
                f"[{a['pmid']}] {a['title'][:80]}\nResumo: {a['abstract'][:200] if a.get('abstract') else 'N/A'}"
                for a in articles[:2]
            ])

            result = await chain.ainvoke({
                "input": f"Pergunta: {query}\n\nArtigos:\n{articles_summary}"
            })

            return AgentResult(
                agent_name=self.name,
                status="success",
                output=result,
                data={"articles_processed": len(articles)}
            )
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return AgentResult(
                agent_name=self.name,
                status="error",
                output=f"Erro ao extrair insights: {str(e)}",
                data={"error": str(e)}
            )


class ValidationAgent:
    """Agent 4: Validates and refutes claims based on evidence."""

    def __init__(self):
        self.model = get_groq_model()
        self.name = "Validation Agent"

    async def execute(
        self,
        query: str,
        initial_response: str,
        articles: List[dict],
        agent_results: List[AgentResult]
    ) -> AgentResult:
        """
        Review the initial response and validate against evidence.
        Flag unsupported claims or contradictions.
        """
        if not articles:
            return AgentResult(
                agent_name=self.name,
                status="success",
                output="Não há artigos para validação.",
                data={"validations": []}
            )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Você é um fact-checker científico rigoroso. Analise a resposta fornecida:
1. Quais afirmações têm suporte nos artigos?
2. Quais afirmações carecem de evidência?
3. Há contradições com os dados?
4. O tom é apropriado (confiante vs especulativo)?

Formato:
VALIDAÇÃO DE AFIRMAÇÕES:
✓ [Afirmação] - Apoiada por [PMID, PMID]
✗ [Afirmação] - NÃO encontrada nos artigos
⚠ [Afirmação] - Controversa (artigos divergem)

CONFIABILIDADE GERAL:
[Score: ALTA / MÉDIA / BAIXA]

RECOMENDAÇÕES DE REVISÃO:
- [Se precisar ajustes]

PONTOS FORTES:
- [Aspectos bem fundamentados]

CRÍTICAS:
- [Pontos fracos]"""
            ),
            ("human", "{input}")
        ])

        chain = prompt | self.model | StrOutputParser()

        try:
            articles_evidence = "\n".join([
                f"[{a['pmid']}] {a['title']}: {a['abstract'][:200]}..."
                for a in articles[:8]
            ])

            other_agents_summary = "\n".join([
                f"{r.agent_name}: {r.output[:300]}..."
                for r in agent_results if r.status == "success"
            ])

            result = await chain.ainvoke({
                "input": f"""Resposta a validar:
\"{initial_response}\"

Pergunta original: {query}

Evidências disponíveis:
{articles_evidence}

Análise de outros agentes:
{other_agents_summary}"""
            })

            return AgentResult(
                agent_name=self.name,
                status="success",
                output=result,
                data={"articles_checked": len(articles)}
            )
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return AgentResult(
                agent_name=self.name,
                status="error",
                output=f"Erro ao validar: {str(e)}",
                data={"error": str(e)}
            )


class KnowledgeGraphAgent:
    """Agent 5: Extracts medical knowledge graph relations."""

    def __init__(self):
        self.model = get_groq_model()
        self.name = "Knowledge Graph Agent"

    async def execute(self, query: str, articles: List[dict]) -> AgentResult:
        """
        Extract entities and relations for disease → gene → protein → drug graph.
        """
        if not articles:
            return AgentResult(
                agent_name=self.name,
                status="success",
                output="Nenhum artigo disponível para extração de grafo.",
                data={"graph_nodes": [], "graph_edges": []}
            )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Você é um extrator de conhecimento biomédico. Identifique entidades e relações do tipo:
- doença
- gene
- proteína
- droga

Retorne o resultado estritamente em JSON com as chaves: nodes, edges, summary.

nodes: lista de objetos {{id, label, type, metadata}}
edges: lista de objetos {{source, target, relation, metadata}}

Relações desejadas: disease->gene, gene->protein, protein->drug, drug->disease, gene->drug.

Exemplo:
{{
  \"nodes\": [
    {{\"id\": \"d1\", \"label\": \"Alzheimer\", \"type\": \"disease\"}},
    {{\"id\": \"g1\", \"label\": \"APOE4\", \"type\": \"gene\"}}
  ],
  \"edges\": [
    {{\"source\": \"d1\", \"target\": \"g1\", \"relation\": \"associated_with\"}}
  ],
  \"summary\": \"Breve explicação das conexões.\"
}}
"""
            ),
            ("human", "{input}")
        ])

        chain = prompt | self.model | StrOutputParser()

        article_text = "\n\n".join([
            f"[{a['pmid']}] {a['title']}\nResumo: {a['abstract']}"
            for a in articles[:5]
        ])

        try:
            raw = await chain.ainvoke({
                "input": f"Pergunta: {query}\n\nArtigos:\n{article_text}"
            })
            graph = self._parse_graph_json(raw)
            return AgentResult(
                agent_name=self.name,
                status="success",
                output=graph.get("summary", "Grafo extraído."),
                data={
                    "graph_nodes": graph.get("nodes", []),
                    "graph_edges": graph.get("edges", []),
                    "graph_summary": graph.get("summary", "")
                }
            )
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return AgentResult(
                agent_name=self.name,
                status="error",
                output=f"Erro ao extrair grafo: {str(e)}",
                data={"error": str(e), "raw_output": raw if 'raw' in locals() else ""}
            )

    def _parse_graph_json(self, raw: str) -> Dict[str, Any]:
        try:
            payload = json.loads(raw)
            return {
                "nodes": payload.get("nodes", []),
                "edges": payload.get("edges", []),
                "summary": payload.get("summary", "")
            }
        except Exception:
            # Tenta extrair JSON em texto se houver prefixos
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(raw[start:end+1])
                except Exception:
                    pass
            return {"nodes": [], "edges": [], "summary": raw}


class TextAnalysisAgent:
    """Agent 6: Extracts methodology, results and structured summaries."""

    def __init__(self):
        self.model = get_groq_model()
        self.name = "Text Analysis Agent"

    async def execute(self, articles: List[dict]) -> AgentResult:
        if not articles:
            return AgentResult(
                agent_name=self.name,
                status="success",
                output="Nenhum artigo para análise de texto.",
                data={"methodology": [], "results": [], "summary": ""}
            )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Você é um analista científico especializado em extração de metodologia e resultados.
1. Extraia a metodologia usada nos artigos.
2. Extraia os principais resultados.
3. Gere um sumário estruturado com bullets.

Formato:
METODOLOGIA:
- ...
RESULTADOS PRINCIPAIS:
- ...
SUMÁRIO:
- ...
"""
            ),
            ("human", "{input}")
        ])

        chain = prompt | self.model | StrOutputParser()

        articles_brief = "\n\n".join([
            f"[{a['pmid']}] {a['title']}\nResumo: {a['abstract']}"
            for a in articles[:5]
        ])

        try:
            result = await chain.ainvoke({"input": f"Artigos:\n{articles_brief}"})
            return AgentResult(
                agent_name=self.name,
                status="success",
                output=result,
                data={"summary": result}
            )
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return AgentResult(
                agent_name=self.name,
                status="error",
                output=f"Erro ao analisar texto: {str(e)}",
                data={"error": str(e)}
            )


class ClarifyingQuestionAgent:
    """Agent 7: Generates clarifying follow-up questions."""

    def __init__(self):
        self.model = get_groq_model()
        self.name = "Clarifying Question Agent"

    async def execute(self, query: str, articles: List[dict]) -> AgentResult:
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """Você é um assistente que identifica quando uma pergunta do usuário precisa de clarificações.
Gerar até 3 perguntas de seguimento que ajudam a aprofundar a pesquisa.
Se a pergunta já estiver clara, responda com uma lista curta de perguntas úteis para expandir o tema.

Formato:
- Pergunta 1
- Pergunta 2
"""
            ),
            ("human", "{input}")
        ])

        chain = prompt | self.model | StrOutputParser()

        articles_summary = "\n".join([f"[{a['pmid']}] {a['title']}" for a in articles[:5]])

        try:
            result = await chain.ainvoke({
                "input": f"Pergunta original: {query}\n\nArtigos disponíveis:\n{articles_summary}"
            })
            questions = [line.strip("- \n") for line in result.splitlines() if line.strip()]
            return AgentResult(
                agent_name=self.name,
                status="success",
                output=result,
                data={"questions": questions[:3]}
            )
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return AgentResult(
                agent_name=self.name,
                status="error",
                output=f"Erro ao gerar perguntas de clarificação: {str(e)}",
                data={"error": str(e)}
            )


class MemoryStore:
    """Simple in-memory session memory store."""

    _store: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_context(cls, session_id: str) -> Dict[str, Any]:
        return cls._store.get(session_id, {})

    @classmethod
    def update_memory(
        cls,
        session_id: str,
        query: str,
        entities: List[dict] = None,
        summary: str = None,
        clarifying_questions: List[str] = None
    ):
        if not session_id:
            return
        record = cls._store.get(session_id, {})
        record["last_query"] = query
        if entities is not None:
            record.setdefault("entities", []).extend(entities)
        if summary:
            record["summary"] = summary
        if clarifying_questions:
            record["clarifying_questions"] = clarifying_questions
        record["updated_at"] = __import__("time").time()
        cls._store[session_id] = record


class MultiAgentOrchestrator:
    """Coordinates all agents in a reasoning pipeline."""

    def __init__(self):
        self.search_agent = PubMedSearchAgent()
        self.quality_agent = QualityAnalysisAgent()
        self.insight_agent = InsightExtractionAgent()
        self.knowledge_graph_agent = KnowledgeGraphAgent()
        self.text_analysis_agent = TextAnalysisAgent()
        self.clarifying_agent = ClarifyingQuestionAgent()
        self.validation_agent = ValidationAgent()
        self.model = get_groq_model()
        self.agent_timeout = int(os.getenv("AGENT_TIMEOUT_SECS", "30"))
        # Limit number of concurrent LLM agent calls to avoid rate limits
        concurrency = int(os.getenv("AGENT_CONCURRENCY", "1"))
        self._semaphore = asyncio.Semaphore(concurrency)

    async def _run_agent(self, agent, *args, agent_key: str) -> AgentResult:
        start = time.time()
        logger.debug(f"[AGENT START] {agent.name} (key={agent_key})")
        async with self._semaphore:
            try:
                res = await asyncio.wait_for(agent.execute(*args), timeout=self.agent_timeout)
                elapsed = time.time() - start
                logger.debug(f"[AGENT OK] {agent.name} (key={agent_key}) elapsed={elapsed:.2f}s")
                return res
            except asyncio.TimeoutError:
                elapsed = time.time() - start
                logger.error(f"[AGENT TIMEOUT] {agent.name} (key={agent_key}) after {elapsed:.2f}s")
                return AgentResult(
                    agent_name=agent.name,
                    status="error",
                    output=f"Timeout de {self.agent_timeout}s no agente {agent.name}",
                    data={"error": "timeout"}
                )
            except Exception as e:
                elapsed = time.time() - start
                logger.exception(f"[AGENT ERROR] {agent.name} (key={agent_key}) after {elapsed:.2f}s: {e}")
                return AgentResult(
                    agent_name=agent.name,
                    status="error",
                    output=f"Erro no agente {agent.name}: {str(e)}",
                    data={"error": str(e)}
                )

    async def _run_with_timeout(self, coro, step_name: str, fallback: str = None) -> str:
        try:
            return await asyncio.wait_for(coro, timeout=self.agent_timeout)
        except asyncio.TimeoutError:
            logger.error(f"Timeout in {step_name} after {self.agent_timeout}s")
            return fallback or "A síntese final excedeu o tempo limite; usando a resposta atual disponível."

    async def execute(
        self,
        query: str,
        articles: List[dict],
        context: str,
        chat_history: List = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Execute multi-agent reasoning pipeline.
        All agents execute - optimizations focus on speed without removing features.
        """
        logger.info(f"Starting multi-agent reasoning for query: {query}")

        memory_context = MemoryStore.get_context(session_id) if session_id else {}
        results = {
            "query": query,
            "agents": {},
            "final_response": None,
            "graph_nodes": [],
            "graph_edges": [],
            "recommendations": [],
            "clarifying_questions": [],
            "memory_summary": memory_context.get("summary", ""),
        }

        # Agent 1: Search & Selection
        logger.info("Executing Agent 1: PubMed Search")
        articles_limited = articles[:3]  # Limit to 3 for speed
        search_result = await self._run_agent(self.search_agent, query, articles_limited, agent_key="search")
        results["agents"]["search"] = search_result

        # Run independent analysis agents in parallel to reduce latency
        logger.info("Executing analysis agents in parallel")
        quality_task = self._run_agent(self.quality_agent, articles_limited, agent_key="quality")
        insight_task = self._run_agent(self.insight_agent, query, articles_limited, context, agent_key="insight")
        graph_task = self._run_agent(self.knowledge_graph_agent, query, articles_limited, agent_key="knowledge_graph")
        text_task = self._run_agent(self.text_analysis_agent, articles_limited, agent_key="text_analysis")
        clarifying_task = self._run_agent(self.clarifying_agent, query, articles_limited, agent_key="clarifying")

        quality_result, insight_result, graph_result, text_analysis_result, clarifying_result = await asyncio.gather(
            quality_task,
            insight_task,
            graph_task,
            text_task,
            clarifying_task,
        )

        results["agents"]["quality"] = quality_result
        results["agents"]["insight"] = insight_result
        results["agents"]["knowledge_graph"] = graph_result
        results["graph_nodes"] = graph_result.data.get("graph_nodes", [])
        results["graph_edges"] = graph_result.data.get("graph_edges", [])
        results["agents"]["text_analysis"] = text_analysis_result
        results["agents"]["clarifying"] = clarifying_result
        results["clarifying_questions"] = clarifying_result.data.get("questions", [])

        # Generate intermediate response
        intermediate_response = await self._generate_response(
            query,
            search_result,
            insight_result,
            text_analysis_result,
            memory_context,
            chat_history
        )

        # Agent 4: Validation
        logger.info("Executing Agent 4: Validation")
        agent_results = [search_result, quality_result, insight_result, graph_result, text_analysis_result]
        validation_result = await self._run_agent(
            self.validation_agent,
            query,
            intermediate_response,
            articles_limited,
            agent_results,
            agent_key="validation"
        )
        results["agents"]["validation"] = validation_result

        # Recommendations
        results["recommendations"] = self._generate_recommendations(
            insight_result, quality_result, graph_result, clarifying_result
        )

        # Final response
        final_response = await self._run_with_timeout(
            self._synthesize_final_response(intermediate_response, validation_result),
            step_name="final synthesis",
            fallback=intermediate_response
        )
        results["final_response"] = final_response

        # Update memory store
        MemoryStore.update_memory(
            session_id=session_id,
            query=query,
            entities=[node for node in results["graph_nodes"] if node.get("type")],
            summary=text_analysis_result.output,
            clarifying_questions=results["clarifying_questions"]
        )

        logger.info("Multi-agent reasoning completed")
        return results

    async def _generate_response(
        self,
        query: str,
        search_result: AgentResult,
        insight_result: AgentResult,
        text_analysis_result: AgentResult,
        memory_context: Dict[str, Any] = None,
        chat_history: List = None
    ) -> str:
        """Generate intermediate response from search, insights and text analysis."""
        memory_text = ""
        if memory_context:
            memory_text = f"Resumo de contexto anterior: {memory_context.get('summary', '')[:200]}\n"

        history_text = ""
        if chat_history:
            def _message_role(msg):
                if hasattr(msg, "role"):
                    return getattr(msg, "role")
                cls_name = msg.__class__.__name__
                if cls_name.lower().endswith("message"):
                    return cls_name[:-7].lower()
                return cls_name.lower()

            history_text = "\n".join(
                f"{_message_role(item).capitalize()}: {item.content.strip()}"
                for item in chat_history
                if getattr(item, 'content', None) and item.content.strip()
            )
            if history_text:
                history_text = f"Histórico de chat:\n{history_text}\n\n"

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Você é um assistente médico avançado. Responda diretamente à pergunta com um texto fluido e completo, evite dividir em tópicos ou criar seções de recomendações, sugestões ou perguntas de follow-up."
            ),
            ("human", "{input}")
        ])

        chain = prompt | self.model | StrOutputParser()

        try:
            insight_truncated = (insight_result.output or "")[:600]
            text_analysis_truncated = (text_analysis_result.output or "")[:600]

            return await chain.ainvoke({
                "input": (
                    f"{history_text}Pergunta: {query}\n\n"
                    f"Baseie sua resposta nos principais insights e na análise de texto. Forneça mais informações sobre o tópico, de maneira clara e contínua.\n\n"
                    f"Insights: {insight_truncated}\n\n"
                    f"Análise de texto: {text_analysis_truncated}\n\n"
                    f"Contexto adicional: {memory_text}"
                )
            })
        except Exception as e:
            if _is_rate_limit_error(e):
                logger.warning("Rate limit hit during intermediate response synthesis; using agent outputs")
            else:
                logger.error(f"Error generating intermediate response: {e}")
            return (
                f"Pergunta: {query}\n\n"
                f"Insights: {insight_result.output[:500]}\n\n"
                f"Análise: {text_analysis_result.output[:500]}"
            )

    async def _synthesize_final_response(
        self, intermediate: str, validation: AgentResult
    ) -> str:
        """Synthesize final response incorporating validation feedback."""
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Você é um editor científico. Refine a resposta com mais informações relevantes sobre o tópico original, mantendo clareza e precisão. Não crie seções de recomendações, perguntas de follow-up ou listas de tópicos."
            ),
            ("human", "{input}")
        ])

        chain = prompt | self.model | StrOutputParser()

        try:
            return await chain.ainvoke({
                "input": (
                    f"Resposta inicial: {intermediate}\n\n"
                    f"Feedback de validação: {validation.output[:400]}\n\n"
                    f"Refine essa resposta com informações adicionais relevantes ao tópico original. Não adicione seções de recomendações, perguntas de follow-up ou listas de tópicos."
                )
            })
        except Exception as e:
            if _is_rate_limit_error(e):
                logger.warning("Rate limit hit during final synthesis; using intermediate response")
            else:
                logger.error(f"Error synthesizing final response: {e}")
            return intermediate

    def _generate_recommendations(
        self,
        insight_result: AgentResult,
        quality_result: AgentResult,
        graph_result: AgentResult,
        clarifying_result: AgentResult
    ) -> List[str]:
        recommendations = []
        if graph_result.data.get("graph_nodes"):
            recommendations.append(
                "Use o grafo de conhecimento para explorar conexões entre doenças, genes, proteínas e medicamentos."
            )
        if quality_result.status == "success":
            recommendations.append("Considere focar nos artigos com maior pontuação de confiabilidade.")
        if clarifying_result.data.get("questions"):
            recommendations.append("Responda às perguntas de clarificação para aprofundar a pesquisa.")
        return recommendations
