import asyncio
from sqlmodel import select

from database import Data
from database import get_async_session_node
from nodes import state

async def add_data_to_db_async(dane: Data):
    try:
        print("3",dane)
        async for session in get_async_session_node():
            print("4",dane)

            session.add(dane)
            await session.commit()
            await session.refresh(dane)
            return True
    except Exception as e:
        print(f"Błąd zapisu async: {e}")
        return False

def add_data_to_db_sync(dane: Data):
    print("1", dane, state.MAIN_LOOP)
    if not state.MAIN_LOOP:
        return False
    print("2", dane)
    future = asyncio.run_coroutine_threadsafe(add_data_to_db_async(dane), state.MAIN_LOOP)
    return future.result()


async def delete_data_from_db_async(data_id: int,username: str):
    """Usuwa rekord o podanym ID (Async)"""
    try:
        async for session in get_async_session_node():
            print(data_id,username)
            statement = select(Data).where(Data.id == int(data_id))
            results = await session.execute(statement)

            data_to_delete = results.scalar_one_or_none()

            if data_to_delete and data_to_delete.username == username:
                await session.delete(data_to_delete)
                await session.commit()
                return True

            return False # Nie znaleziono ID
    except Exception as e:
        print(f"Błąd usuwania async: {e}")
        return False

def delete_data_from_db_sync(data_id: int,username: str):
    if not state.MAIN_LOOP:
        return False
    future = asyncio.run_coroutine_threadsafe(delete_data_from_db_async(data_id,username), state.MAIN_LOOP)
    return future.result()