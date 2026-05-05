"""Baza danych przechowująca dane od użytkowników (Baza wątków)"""

import os
from dotenv import load_dotenv

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .models_schemas_data import *

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL_NODE","postgresql+asyncpg://node_admin:node_password@localhost:5433/node_db")

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def init_db_node():
    """Inicjujemy połączenie z bazą danych"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_async_session_node():
    """Zwracamy połączenie asynchroniczne z bazą danych"""
    async with async_session_maker() as session:
        yield session