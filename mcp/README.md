# MCP - Model Context Protocol Tools

Ferramentas MCP para KlyraAI - Sistema de busca e análise de artigos no PubMed.

## 📁 Arquivos

- **`mcp_pubmed_server.py`** - Servidor MCP que expõe ferramentas para busca no PubMed
- **`mcp_pubmed_client.py`** - Cliente MCP que se conecta ao servidor e chamadas de ferramentas
- **`mcp_servers.json`** - Configuração dos servidores MCP
- **`__init__.py`** - Módulo Python com exports da pasta

## 🚀 Uso

### Iniciar servidor MCP
```bash
python mcp/mcp_pubmed_server.py
```

### Usar cliente MCP (do backend)
```python
from mcp.mcp_pubmed_client import get_mcp_client

# Obter cliente MCP
client = await get_mcp_client()

# Usar ferramentas disponíveis
# O cliente automaticamente conecta e chama ferramentas
```

## 🔧 Ferramentas Disponíveis

### `search_pubmed`
Busca artigos no PubMed por termo médico.

**Parâmetros:**
- `query` (string): Termo de busca
- `max_results` (int): Número máximo de resultados (padrão: 5)

**Retorna:** Lista de IDs de artigos

### `fetch_article_details`
Obtém detalhes dos artigos em formato XML.

**Parâmetros:**
- `article_ids` (list): Lista de IDs de artigos

**Retorna:** XML com detalhes dos artigos

### `parse_articles`
Converte XML em estrutura JSON estruturada.

**Parâmetros:**
- `xml_data` (string): Dados em XML

**Retorna:** Lista de artigos em formato JSON

## 📝 Adicionar Nova Ferramenta

1. **Implemente a função em `mcp_pubmed_server.py`:**
```python
async def nova_ferramenta(parametro: str) -> dict:
    """Descrição da ferramenta"""
    # implementação
    return resultado
```

2. **Registre em `list_tools()`:**
```python
def list_tools(self) -> list[Tool]:
    return [
        Tool(
            name="nova_ferramenta",
            description="Descrição",
            inputSchema={
                "type": "object",
                "properties": {
                    "parametro": {"type": "string"}
                }
            }
        )
    ]
```

3. **Implemente handler em `call_tool()`:**
```python
elif tool_name == "nova_ferramenta":
    result = await nova_ferramenta(tool_input["parametro"])
    return result
```

4. **Crie método wrapper em `mcp_pubmed_client.py`:**
```python
async def nova_ferramenta(self, parametro: str) -> dict:
    """Wrapper para a ferramenta"""
    return await self._call_tool("nova_ferramenta", {"parametro": parametro})
```

## 🔗 Integração com Backend

O backend (`backend.py`) importa e usa o cliente MCP:

```python
from mcp.mcp_pubmed_client import get_mcp_client, shutdown_mcp_client
```

## ⚙️ Configuração

Editar `mcp_servers.json` para adicionar novos servidores:

```json
{
  "mcpServers": {
    "nova-ferramenta": {
      "command": "python",
      "args": ["mcp/nova_ferramenta_server.py"],
      "description": "Descrição"
    }
  }
}
```

## 🐛 Troubleshooting

### Servidor não inicia
```bash
# Verifique se pode rodar
python mcp/mcp_pubmed_server.py

# Verifique Python
which python
```

### Ferramenta não é encontrada
- Verifique se está registrada em `list_tools()`
- Verifique nomes (case-sensitive)
- Restart do servidor

### Timeout na conexão
- Aumentar timeout em cliente
- Verificar conexão de rede
- Ver logs do servidor

## 📚 Referências

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25499/)
- [PubMed API](https://pubmed.ncbi.nlm.nih.gov/tools/developers/)
