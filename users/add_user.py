"""
Script para adicionar um usuário ao banco de dados.
Uso: python add_user.py [username] [password]
"""
import asyncio
import sys
from databases.database import init_db, create_user, user_exists


async def add_user(username: str, password: str):
    """
    Adiciona um usuário ao banco de dados.
    
    Args:
        username: Nome de usuário
        password: Senha
    """
    # Garante que o banco está inicializado
    await init_db()
    
    # Verifica se o usuário já existe
    if await user_exists(username):
        print(f"❌ Erro: O usuário '{username}' já existe no banco de dados.")
        return False
    
    # Cria o usuário
    success = await create_user(username, password)
    
    if success:
        print(f"✅ Usuário '{username}' criado com sucesso!")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        return True
    else:
        print(f"❌ Erro ao criar o usuário '{username}'.")
        return False


async def main():
    """
    Função principal que processa argumentos da linha de comando.
    """
    if len(sys.argv) == 3:
        # Usuário forneceu username e password como argumentos
        username = sys.argv[1]
        password = sys.argv[2]
    elif len(sys.argv) == 1:
        # Usuário não forneceu argumentos, usa valores padrão para teste
        username = "teste"
        password = "teste123"
        print("Usando valores padrão para teste:")
    else:
        print("Uso: python add_user.py [username] [password]")
        print("Exemplo: python add_user.py meuusuario minhasenha")
        print("\nOu execute sem argumentos para criar usuário de teste padrão:")
        print("python add_user.py")
        sys.exit(1)
    
    await add_user(username, password)


if __name__ == "__main__":
    asyncio.run(main())

