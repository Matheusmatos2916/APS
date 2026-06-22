"""
MCP (Model Context Protocol) Tools para KlyraAI

Este módulo contém ferramentas MCP para busca e análise de artigos no PubMed.
"""

from .mcp_pubmed_client import get_mcp_client, shutdown_mcp_client

__all__ = ["get_mcp_client", "shutdown_mcp_client"]
