# Databases - Módulo de Banco de Dados

Módulo que centraliza toda a gestão de bancos de dados do KlyraAI.

## 📁 Arquivos

- **`database.py`** - Módulo principal com operações de banco de dados
- **`users.db`** - SQLite com dados de usuários (autenticação)
- **`agent_memory.db`** - SQLite com memória de agentes
- **`chainlit.db`** - SQLite com dados da interface Chainlit
- **`init_chainlit_db.sql`** - Script SQL para inicializar Chainlit
- **`__init__.py`** - Módulo Python com exports

## 🗄️ Estrutura dos Bancos de Dados

### users.db
Armazena dados de autenticação de usuários.

**Tabela: users**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### agent_memory.db
Armazena histórico e memória dos agentes multi-agente.

### chainlit.db
Gerenciado pelo Chainlit, armazena:
- Histórico de conversas
- Dados de sessão
- Logs de interações

## 🚀 Como Usar

### Importar do módulo
```python
from databases import init_db, create_user, verify_user, user_exists
```

### Importar direto do arquivo
```python
from databases.database import init_db, create_user, verify_user, user_exists
```

## 🔐 Funções Disponíveis

### `init_db()`
Inicializa o banco de dados criando tabelas se não existirem.

```python
await init_db()
```

### `create_user(username, password)`
Cria novo usuário com senha hash.

```python
username = "user@example.com"
password = "senha_segura"
await create_user(username, password)
```

### `verify_user(username, password)`
Verifica credenciais de usuário.

```python
is_valid = await verify_user(username, password)
```

### `user_exists(username)`
Verifica se usuário existe.

```python
exists = await user_exists(username)
```

## 🔒 Segurança

- Senhas são hash com bcrypt (não são armazenadas em texto plano)
- Banco de dados é local (não sincronizado)
- Use variáveis de ambiente para caminhos em produção

## 📊 Backup

### Fazer backup de users.db
```bash
# Windows
copy databases\users.db databases\users.db.backup

# Linux/Mac
cp databases/users.db databases/users.db.backup
```

### Restaurar backup
```bash
# Windows
copy databases\users.db.backup databases\users.db

# Linux/Mac
cp databases/users.db.backup databases/users.db
```

## 🔄 Migrações

Ao alterar schema dos bancos:

1. Editar `database.py` com novo schema
2. Deletar arquivo `.db` (vai ser recriado)
3. Reiniciar aplicação

**Ou**, para preservar dados:
1. Criar migration script
2. Executar manualmente com aiosqlite

## ⚙️ Configuração

### Variáveis de Ambiente
Adicione ao `.env`:
```env
# Opcional - padrão é databases/users.db
DB_PATH=databases/users.db

# Para Chainlit
DATABASE_CHAINLIT=sqlite:///./databases/chainlit.db
```

### Caminhos Relativos
Todos os caminhos são relativos à raiz do projeto:
- `databases/users.db`
- `databases/agent_memory.db`
- `databases/chainlit.db`

## 🐛 Troubleshooting

### "Database is locked"
- Fechar outras conexões
- Restart da aplicação
- Verificar se há múltiplas instâncias rodando

### "Table does not exist"
- Executar `await init_db()` primeiro
- Deletar arquivo `.db` e deixar recriar

### "Permission denied"
- Verificar permissões da pasta `databases/`
- Em produção, usar `/var/lib/app/databases` com perms 755

### Dados perdidos após restart
- Verificar se arquivo `.db` existe em `databases/`
- Checar .gitignore para não commitar `.db` files

## 📈 Performance

Para melhor performance com grandes volumes:

1. **Adicionar índices:**
```python
await db.execute("CREATE INDEX idx_username ON users(username)")
```

2. **Usar WAL mode:**
```python
await db.execute("PRAGMA journal_mode=WAL")
```

3. **Aumentar cache:**
```python
await db.execute("PRAGMA cache_size=10000")
```

## 📚 Referências

- [aiosqlite](https://github.com/omnilib/aiosqlite)
- [bcrypt](https://github.com/pyca/bcrypt)
- [SQLite Best Practices](https://www.sqlite.org/bestpractice.html)
