#!/usr/bin/env python3
"""
MCP Server for PubMed Search Tools.
Exposes search_pubmed, fetch_article_details, and parse_articles as MCP tools.
"""

import json
import asyncio
from mcp.server import Server
from mcp.types import TextContent, Tool
import logging

from .teste_resquest_pubmed import (
    search_pubmed,
    fetch_article_details,
    parse_articles,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("pubmed-search")


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from MCP client."""
    if name == "search_pubmed":
        query = arguments.get("query", "medicine")
        retmax = arguments.get("retmax", 10)
        logger.info(f"Searching PubMed: {query} (retmax={retmax})")
        ids = await asyncio.to_thread(search_pubmed, query, retmax)
        return [TextContent(type="text", text=json.dumps({"ids": ids}))]

    elif name == "fetch_article_details":
        ids = arguments.get("ids", [])
        if not ids:
            return [TextContent(type="text", text=json.dumps({"error": "No IDs provided"}))]
        logger.info(f"Fetching details for {len(ids)} articles")
        xml_text = await asyncio.to_thread(fetch_article_details, ids)
        return [TextContent(type="text", text=xml_text)]

    elif name == "parse_articles":
        xml_text = arguments.get("xml_text", "")
        if not xml_text:
            return [TextContent(type="text", text=json.dumps({"articles": []}))]
        logger.info("Parsing XML articles")
        articles = await asyncio.to_thread(parse_articles, xml_text)
        return [TextContent(type="text", text=json.dumps({"articles": articles}))]

    else:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="search_pubmed",
            description="Search PubMed for articles by query term. Returns list of article IDs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Medical term or health topic to search for",
                    },
                    "retmax": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-20)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="fetch_article_details",
            description="Fetch full XML details for PubMed articles by their IDs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of PubMed article IDs",
                    }
                },
                "required": ["ids"],
            },
        ),
        Tool(
            name="parse_articles",
            description="Parse PubMed XML response into structured article data (JSON format).",
            inputSchema={
                "type": "object",
                "properties": {
                    "xml_text": {
                        "type": "string",
                        "description": "PubMed XML response text",
                    }
                },
                "required": ["xml_text"],
            },
        ),
    ]


async def main():
    """Run the MCP server."""
    async with server:
        logger.info("PubMed MCP Server started")
        await server.wait_for_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
