"""
Example client for Multi-Agent Reasoning API.
Demonstrates how to call the /api/chat/multi-agent endpoint.
"""

import httpx
import asyncio
import json
from typing import Dict, Any


async def test_multi_agent_chat():
    """Test the multi-agent chat endpoint."""
    
    base_url = "http://localhost:8001"
    
    # Example query
    query = "Qual é o papel do APOE4 na neurodegeneração?"
    
    payload = {
        "query": query,
        "history": [],
        "limit": 5
    }
    
    print("=" * 80)
    print("MULTI-AGENT REASONING SYSTEM")
    print("=" * 80)
    print(f"\nQuery: {query}\n")
    print("Iniciando raciocínio multi-agente...\n")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/api/chat/multi-agent",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            print("\n" + "=" * 80)
            print("RACIOCÍNIO DOS AGENTES")
            print("=" * 80)
            
            print(f"\nCaminho de raciocínio:\n{data['reasoning_path']}\n")
            
            # Agent analyses
            print("\n" + "-" * 80)
            print("ANÁLISE DETALHADA POR AGENTE")
            print("-" * 80)
            
            for agent_key, analysis in data.get("agent_analyses", {}).items():
                print(f"\n[{analysis['agent_name']}] Status: {analysis['status'].upper()}")
                print(f"{'=' * 70}")
                print(analysis['output'][:500] + "..." if len(analysis['output']) > 500 else analysis['output'])
                if analysis.get('data'):
                    print(f"\nDados: {json.dumps(analysis['data'], indent=2, ensure_ascii=False)}")
            
            # Final response
            print("\n" + "=" * 80)
            print("RESPOSTA FINAL CONSOLIDADA")
            print("=" * 80)
            print(f"\n{data['final_response']}\n")
            
            # References
            if data.get('references'):
                print("\n" + "-" * 80)
                print("REFERÊNCIAS")
                print("-" * 80)
                print(data['references'])
            
            # Articles
            print(f"\n\nArtigos analisados: {len(data.get('articles', []))}")
            for i, article in enumerate(data.get('articles', [])[:3], 1):
                print(f"\n{i}. [{article['pmid']}] {article['title']}")
                print(f"   {article['journal']} ({article['year']})")
                print(f"   {article['authors']}")
            
    except httpx.HTTPError as e:
        print(f"[ERROR] HTTP Error: {e}")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")


async def compare_endpoints():
    """Compare standard vs multi-agent endpoints."""
    
    base_url = "http://localhost:8001"
    query = "O que é Alzheimer?"
    
    payload = {
        "query": query,
        "history": [],
        "limit": 3
    }
    
    print("\n" + "=" * 80)
    print("COMPARAÇÃO: ENDPOINT PADRÃO vs MULTI-AGENT")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Standard endpoint
            print("\n[1] Testando /api/chat (endpoint padrão)...")
            resp1 = await client.post(f"{base_url}/api/chat", json=payload)
            resp1.raise_for_status()
            data1 = resp1.json()
            print(f"    Resposta: {len(data1['response'])} caracteres")
            print(f"    Refs: {data1.get('references', 'N/A')[:50]}...")
            
            # Multi-agent endpoint
            print("\n[2] Testando /api/chat/multi-agent (multi-agente)...")
            resp2 = await client.post(f"{base_url}/api/chat/multi-agent", json=payload)
            resp2.raise_for_status()
            data2 = resp2.json()
            print(f"    Resposta final: {len(data2['final_response'])} caracteres")
            print(f"    Agentes executados: {len(data2.get('agent_analyses', {}))}")
            print(f"    Refs: {data2.get('references', 'N/A')[:50]}...")
            
            print("\n✓ Ambos endpoints funcionando!")
            
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("KlyraAI - Multi-Agent Reasoning System")
    print("=" * 80)
    
    # Test multi-agent
    asyncio.run(test_multi_agent_chat())
    
    # Compare endpoints
    # asyncio.run(compare_endpoints())
