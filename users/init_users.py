"""
Script para inicializar o banco de dados com usuários de exemplo.
Execute este script para criar usuários no banco de dados.
"""
import asyncio
from databases.database import init_db, create_user


async def main():
    """
    Inicializa o banco de dados e cria usuários de exemplo.
    """
    print("Inicializando banco de dados...")
    await init_db()
    print("Banco de dados inicializado!")
    
    # Lista de usuários de exemplo
    users = [
        ("admin", "admin123"),
        ("usuario1", "senha123"),
        ("teste", "teste123"),
    ]
    
    print("\nCriando usuários...")
    for username, password in users:
        success = await create_user(username, password)
        if success:
            print(f"✓ Usuário '{username}' criado com sucesso")
        else:
            print(f"✗ Usuário '{username}' já existe ou houve erro ao criar")
    
    print("\nInicialização concluída!")
    print("\nUsuários disponíveis:")
    for username, password in users:
        print(f"  - Username: {username}, Password: {password}")


if __name__ == "__main__":
    asyncio.run(main())

