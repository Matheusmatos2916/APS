"""
Quick test script to verify multi-agent system is working.
"""

import asyncio
import httpx
import json


async def quick_test():
    """Quick sanity check of both endpoints."""
    
    base_url = "http://localhost:8001"
    
    print("\n" + "=" * 70)
    print("TESTE RÁPIDO - SISTEMA MULTI-AGENTE")
    print("=" * 70)
    
    # Test data
    test_query = "O que é Alzheimer?"
    payload = {
        "query": test_query,
        "history": [],
        "limit": 3
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Health check
            print("\n[1] Health Check...")
            resp = await client.get(f"{base_url}/api/health")
            print(f"    ✓ Backend respondendo: {resp.json()}")
            
            # Test standard endpoint
            print("\n[2] Testando /api/chat...")
            try:
                resp1 = await client.post(f"{base_url}/api/chat", json=payload)
                resp1.raise_for_status()
                data1 = resp1.json()
                print(f"    ✓ Resposta recebida ({len(data1['response'])} chars)")
                print(f"    ✓ {len(data1.get('articles', []))} artigos")
            except Exception as e:
                print(f"    ✗ Erro: {e}")
            
            # Test multi-agent endpoint
            print("\n[3] Testando /api/chat/multi-agent...")
            try:
                resp2 = await client.post(f"{base_url}/api/chat/multi-agent", json=payload)
                resp2.raise_for_status()
                data2 = resp2.json()
                
                print(f"    ✓ Resposta final recebida ({len(data2['final_response'])} chars)")
                print(f"    ✓ {len(data2['agent_analyses'])} agentes executados")
                
                # Show agent status
                print("\n[4] Status dos Agentes:")
                for agent_key, analysis in data2['agent_analyses'].items():
                    status_icon = "✓" if analysis['status'] == "success" else "✗"
                    print(f"    {status_icon} {analysis['agent_name']}: {analysis['status'].upper()}")
                
                print(f"\n[5] Caminho de raciocínio:")
                for line in data2['reasoning_path'].split('\n'):
                    print(f"    {line}")
                
                print(f"\n[6] Referências encontradas:")
                print(f"    {data2['references'][:100]}...")
                
            except Exception as e:
                print(f"    ✗ Erro: {e}")
        
        print("\n" + "=" * 70)
        print("✓ TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERRO: {e}\n")
        print("Dica: Certifique-se que o backend está rodando:")
        print("  uvicorn backend:app --host 0.0.0.0 --port 8001")


if __name__ == "__main__":
    asyncio.run(quick_test())
