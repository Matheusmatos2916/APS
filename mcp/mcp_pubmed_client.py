"""
MCP Client for PubMed Search (Simplified).
Wraps PubMed search functions for integration with FastAPI backend.
"""

import asyncio
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

from .teste_resquest_pubmed import search_pubmed, fetch_article_details, parse_articles


class MCPPubMedClient:
    """Simplified client for PubMed operations."""

    def __init__(self):
        pass

    async def start(self):
        """No-op start method for compatibility."""
        logger.info("MCP PubMed Client initialized")

    async def stop(self):
        """No-op stop method for compatibility."""
        logger.info("MCP PubMed Client stopped")

    async def search_pubmed(self, query: str, retmax: int = 10) -> List[str]:
        """Search PubMed and return article IDs."""
        try:
            ids = await asyncio.to_thread(search_pubmed, query, retmax)
            return ids
        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            return []

    async def fetch_article_details(self, ids: List[str]) -> str:
        """Fetch full XML details for articles."""
        if not ids:
            return ""
        try:
            xml_text = await asyncio.to_thread(fetch_article_details, ids)
            return xml_text
        except Exception as e:
            logger.error(f"Error fetching article details: {e}")
            return ""

    async def parse_articles(self, xml_text: str) -> List[dict]:
        """Parse articles from XML."""
        if not xml_text:
            return []
        try:
            articles = await asyncio.to_thread(parse_articles, xml_text)
            return articles
        except Exception as e:
            logger.error(f"Error parsing articles: {e}")
            return []

    async def search_and_parse(self, query: str, limit: int = 5) -> tuple[str, List[dict]]:
        """Convenience method to search, fetch, and parse in one call."""
        ids = await self.search_pubmed(query, retmax=max(limit, 10))
        if not ids:
            return "", []

        ids = ids[:limit]
        xml_text = await self.fetch_article_details(ids)
        articles = await self.parse_articles(xml_text)
        
        # Build context from articles
        context_parts = []
        for i, a in enumerate(articles, start=1):
            links_str = ""
            if a.get("full_text_links"):
                links_str = "\n  Links: " + "; ".join(
                    f"{label}: {url}" for label, url in a["full_text_links"]
                )
            context_parts.append(
                f"[{i}] PMID: {a.get('pmid', '—')}  |  {a.get('journal', '—')}  ({a.get('year', '—')})\n"
                f"Título: {a.get('title', '—')}\n"
                f"DOI: {a.get('doi', '—')}\n"
                f"Autores: {a.get('authors', '—')}\n"
                f"Resumo: {a.get('abstract', '(sem resumo)')}{links_str}"
            )
        context = "\n\n---\n\n".join(context_parts) if context_parts else ""
        return context, articles


# Global client instance
_mcp_client: Optional[MCPPubMedClient] = None


async def get_mcp_client() -> MCPPubMedClient:
    """Get or create the global MCP client."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPPubMedClient()
        await _mcp_client.start()
    return _mcp_client


async def shutdown_mcp_client():
    """Shutdown the global MCP client."""
    global _mcp_client
    if _mcp_client:
        await _mcp_client.stop()
        _mcp_client = None
