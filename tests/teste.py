import os
import dotenv
import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

from databases.database import init_db, verify_user

# carrega variáveis do .env
dotenv.load_dotenv()

url_database = os.getenv("DATABASE_CHAINLIT")


# -----------------------------
# LOGIN (PÁGINA DE LOGIN)
# -----------------------------
@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    """
    Tela de login do Chainlit.
    Verifica usuário e senha no banco.
    """

    # garante que o banco está inicializado
    await init_db()
    

    # verifica usuário no banco
    if await verify_user(username, password):
        return cl.User(identifier=username)



    return None


# -----------------------------
# BANCO DO CHAINLIT
# -----------------------------
@cl.data_layer
def get_data_layer():
    """
    Define o banco usado pelo Chainlit
    para salvar usuários, threads e mensagens.
    """
    return SQLAlchemyDataLayer(conninfo=url_database)


# -----------------------------
# APÓS LOGIN
# -----------------------------
@cl.on_chat_start
async def start():
    await cl.Message(
        content="""✅ **Login realizado com sucesso!**
"""
    ).send()