"""
Módulo de banco de dados para autenticação de usuários.
"""
import aiosqlite
import hashlib
import os
from typing import Optional

import bcrypt

# Caminho do banco de dados
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


async def init_db():
    """
    Inicializa o banco de dados criando a tabela de usuários se não existir.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


def hash_password(password: str) -> str:
    """
    Gera um hash bcrypt da senha.
    
    Args:
        password: Senha em texto plano
        
    Returns:
        Hash bcrypt (string) para persistência no banco
    """
    if password is None:
        raise ValueError("password não pode ser None")
    pw_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def _is_bcrypt_hash(value: str) -> bool:
    # Formatos comuns: $2a$, $2b$, $2y$
    return isinstance(value, str) and value.startswith("$2")


def _legacy_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


async def create_user(username: str, password: str) -> bool:
    """
    Cria um novo usuário no banco de dados.
    
    Args:
        username: Nome de usuário
        password: Senha em texto plano
        
    Returns:
        True se o usuário foi criado com sucesso, False caso contrário
    """
    try:
        password_hash = hash_password(password)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        # Usuário já existe
        return False


async def verify_user(username: str, password: str) -> bool:
    """
    Verifica se as credenciais do usuário estão corretas.
    
    Args:
        username: Nome de usuário
        password: Senha em texto plano
        
    Returns:
        True se as credenciais estão corretas, False caso contrário
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or not row[0]:
                return False

            stored = row[0]

            # bcrypt (padrão atual)
            if _is_bcrypt_hash(stored):
                try:
                    return bcrypt.checkpw(
                        password.encode("utf-8"),
                        stored.encode("utf-8"),
                    )
                except Exception:
                    return False

            # SHA-256 legado (compatibilidade): valida e migra para bcrypt
            if stored == _legacy_sha256(password):
                new_hash = hash_password(password)
                await db.execute(
                    "UPDATE users SET password_hash = ? WHERE username = ?",
                    (new_hash, username),
                )
                await db.commit()
                return True
    return False


async def user_exists(username: str) -> bool:
    """
    Verifica se um usuário existe no banco de dados.
    
    Args:
        username: Nome de usuário
        
    Returns:
        True se o usuário existe, False caso contrário
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (username,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None

