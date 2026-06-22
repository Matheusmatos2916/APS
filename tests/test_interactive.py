"""
Interactive client to test both standard and multi-agent endpoints.
"""

import asyncio
import httpx
import json
from typing import Literal


async def test_endpoint(
    query: str,
    mode: Literal["standard", "multi-agent", "both"] = "both",
    limit: int = 3
):
    """Test endpoint with given query."""
    
    base_url = "http://localhost:8001"
    payload = {
        "query": query,
        "history": [],
        "limit": limit
    }
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        if mode in ["standard", "both"]:
            print("\n" + "=" * 70)
            print("📝 MODO PADRÃO (/api/chat)")
            print("=" * 70)
            print(f"Query: {query}\n")
            
            try:
                resp = await client.post(f"{base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                print("📄 Resposta:")
                print(data['response'])
                print(f"\n📚 Artigos: {len(data.get('articles', []))}")
                for i, article in enumerate(data.get('articles', [])[:3], 1):
                    print(f"   {i}. {article['title'][:80]}...")
                    
            except Exception as e:
                print(f"❌ Erro: {e}")
        
        if mode in ["multi-agent", "both"]:
            print("\n" + "=" * 70)
            print("🤖 MODO MULTI-AGENTE (/api/chat/multi-agent)")
            print("=" * 70)
            print(f"Query: {query}\n")
            
            try:
                resp = await client.post(f"{base_url}/api/chat/multi-agent", json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                # Agent results
                print("👥 Agentes Executados:")
                for agent_key, analysis in data['agent_analyses'].items():
                    status_icon = "✓" if analysis['status'] == "success" else "✗"
                    print(f"   {status_icon} {analysis['agent_name']}: {analysis['status'].upper()}")
                    if analysis['output']:
                        print(f"      └─ {analysis['output'][:100]}...")
                
                # Reasoning path
                print("\n💭 Caminho de Raciocínio:")
                for line in data['reasoning_path'].split('\n'):
                    if line.strip():
                        print(f"   {line}")
                
                # Final response
                print("\n📝 Resposta Final:")
                print(data['final_response'])
                
                # References
                print("\n📚 Referências:")
                print(data['references'])
                    
            except Exception as e:
                print(f"❌ Erro: {e}")


async def interactive_mode():
    """Interactive testing mode."""
    
    print("\n" + "=" * 70)
    print("🧪 TESTE INTERATIVO - Sistema Multi-Agente")
    print("=" * 70)
    print("\nComandos:")
    print("  'sair' - Sair do programa")
    print("  'help' - Mostrar ajuda")
    print("\nExemplos de queries:")
    print("  - O que é Alzheimer?")
    print("  - Qual é o tratamento para diabetes tipo 2?")
    print("  - Como funciona a vacina da COVID-19?")
    print("  - Quais são os sintomas da depressão?")
    print("=" * 70)
    
    while True:
        try:
            print("\n📌 Escolha o modo:")
            print("  1 - Modo padrão (/api/chat)")
            print("  2 - Modo multi-agente (/api/chat/multi-agent)")
            print("  3 - Testar ambos")
            print("  0 - Sair")
            
            choice = input("\nOpção (0-3): ").strip()
            
            if choice == "0":
                print("\n✅ Até logo!")
                break
            elif choice == "1":
                mode = "standard"
            elif choice == "2":
                mode = "multi-agent"
            elif choice == "3":
                mode = "both"
            else:
                print("❌ Opção inválida!")
                continue
            
            query = input("\n🔍 Digite sua query: ").strip()
            
            if not query:
                print("❌ Query vazia!")
                continue
            
            if query.lower() == "sair":
                print("\n✅ Até logo!")
                break
            
            if query.lower() == "help":
                print("\nUse queries em português sobre tópicos médicos.")
                print("Exemplos: 'O que é...?', 'Qual é o tratamento de...?'")
                continue
            
            limit = input("\n📊 Quantos artigos? (padrão: 3): ").strip()
            limit = int(limit) if limit.isdigit() else 3
            
            await test_endpoint(query, mode=mode, limit=limit)
            
        except KeyboardInterrupt:
            print("\n\n✅ Interrompido pelo usuário")
            break
        except Exception as e:
            print(f"\n❌ Erro: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(interactive_mode())
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
