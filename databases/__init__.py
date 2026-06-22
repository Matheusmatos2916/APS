"""
Módulo de banco de dados para KlyraAI

Gerencia bancos de dados SQLite para:
- Autenticação de usuários (users.db)
- Memória de agentes (agent_memory.db)
- Configurações Chainlit (chainlit.db)
"""

from .database import init_db, create_user, verify_user, user_exists

__all__ = ["init_db", "create_user", "verify_user", "user_exists"]
