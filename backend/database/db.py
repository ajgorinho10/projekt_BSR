"""Baza danych przechowująca dane o użytkownikach"""

import os
from dotenv import load_dotenv

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .models_user import *

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL","postgresql+asyncpg://bully_admin:bully_password@localhost:5432/bully_db")

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_async_session():
    async with async_session_maker() as session:
        yield session