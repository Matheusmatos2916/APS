"""
Módulo de banco de dados para autenticação de usuários.
"""
import aiosqlite
import hashlib
import os
from typing import Optional

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
    Gera um hash SHA-256 da senha.
    
    Args:
        password: Senha em texto plano
        
    Returns:
        Hash hexadecimal da senha
    """
    return hashlib.sha256(password.encode()).hexdigest()


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
    password_hash = hash_password(password)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == password_hash:
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

