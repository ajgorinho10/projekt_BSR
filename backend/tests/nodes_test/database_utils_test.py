import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from database import Data
from nodes import state
from nodes.database_utils import (
    add_data_to_db_async,
    add_data_to_db_sync,
    delete_data_from_db_async,
    delete_data_from_db_sync,
    get_read_data_async
)


@pytest.fixture
def mock_db_session():
    """Tworzy asynchroniczny mock sesji bazy danych oraz generator, aby poprawnie symulować `async for`."""
    session_mock = AsyncMock()
    
    async def get_session_generator():
        yield session_mock
        
    return get_session_generator, session_mock


@pytest.fixture(autouse=True)
def reset_state():
    """Resetuje stan pętli asynchronicznej przed każdym testem."""
    state.MAIN_LOOP = None
    yield


# --- TESTY: add_data_to_db_async ---

@pytest.mark.asyncio
@patch("nodes.database_utils.get_async_session_node")
async def test_add_data_to_db_async_success(mock_get_session, mock_db_session):
    generator, session = mock_db_session
    mock_get_session.side_effect = generator
    dane = Data(data="test", username="user1")

    result = await add_data_to_db_async(dane)

    session.add.assert_called_once_with(dane)
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(dane)
    assert result == dane


@pytest.mark.asyncio
@patch("nodes.database_utils.get_async_session_node")
async def test_add_data_to_db_async_exception(mock_get_session, mock_db_session):
    generator, session = mock_db_session
    mock_get_session.side_effect = generator
    session.commit.side_effect = Exception("DB Error")
    dane = Data(data="test", username="user1")

    result = await add_data_to_db_async(dane)

    assert result is False


# --- TESTY: add_data_to_db_sync ---

def test_add_data_to_db_sync_no_loop():
    dane = Data(data="test", username="user1")
    result = add_data_to_db_sync(dane)
    assert result is False


@patch("nodes.database_utils.asyncio.run_coroutine_threadsafe")
def test_add_data_to_db_sync_success(mock_run_coroutine):
    state.MAIN_LOOP = MagicMock()
    dane = Data(data="test", username="user1")
    
    mock_future = MagicMock()
    mock_future.result.return_value = dane
    mock_run_coroutine.return_value = mock_future

    result = add_data_to_db_sync(dane)

    mock_run_coroutine.assert_called_once()
    assert result == dane


# --- TESTY: delete_data_from_db_async ---

@pytest.mark.asyncio
@patch("nodes.database_utils.get_async_session_node")
async def test_delete_data_from_db_async_success(mock_get_session, mock_db_session):
    generator, session = mock_db_session
    mock_get_session.side_effect = generator
    
    mock_data = MagicMock()
    mock_data.username = "user1"
    
    mock_results = MagicMock()
    mock_results.scalar_one_or_none.return_value = mock_data
    session.execute.return_value = mock_results

    result = await delete_data_from_db_async(1, "user1")

    session.delete.assert_called_once_with(mock_data)
    session.commit.assert_called_once()
    assert result == 1


@pytest.mark.asyncio
@patch("nodes.database_utils.get_async_session_node")
async def test_delete_data_from_db_async_not_found(mock_get_session, mock_db_session):
    generator, session = mock_db_session
    mock_get_session.side_effect = generator
    
    mock_results = MagicMock()
    mock_results.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_results

    result = await delete_data_from_db_async(1, "user1")

    session.delete.assert_not_called()
    assert result is False


@pytest.mark.asyncio
@patch("nodes.database_utils.get_async_session_node")
async def test_delete_data_from_db_async_wrong_user(mock_get_session, mock_db_session):
    generator, session = mock_db_session
    mock_get_session.side_effect = generator
    
    mock_data = MagicMock()
    mock_data.username = "other_user"
    
    mock_results = MagicMock()
    mock_results.scalar_one_or_none.return_value = mock_data
    session.execute.return_value = mock_results

    result = await delete_data_from_db_async(1, "user1")

    session.delete.assert_not_called()
    assert result is False


@pytest.mark.asyncio
@patch("nodes.database_utils.get_async_session_node")
async def test_delete_data_from_db_async_exception(mock_get_session, mock_db_session):
    generator, session = mock_db_session
    mock_get_session.side_effect = generator
    session.execute.side_effect = Exception("DB Error")

    result = await delete_data_from_db_async(1, "user1")

    assert result is False


# --- TESTY: delete_data_from_db_sync ---

def test_delete_data_from_db_sync_no_loop():
    result = delete_data_from_db_sync(1, "user1")
    assert result is False


@patch("nodes.database_utils.asyncio.run_coroutine_threadsafe")
def test_delete_data_from_db_sync_success(mock_run_coroutine):
    state.MAIN_LOOP = MagicMock()
    
    mock_future = MagicMock()
    mock_future.result.return_value = 1
    mock_run_coroutine.return_value = mock_future

    result = delete_data_from_db_sync(1, "user1")

    mock_run_coroutine.assert_called_once()
    assert result == 1


# --- TESTY: get_read_data_async ---

@pytest.mark.asyncio
@patch("nodes.database_utils.get_async_session_node")
async def test_get_read_data_async_success(mock_get_session, mock_db_session):
    generator, session = mock_db_session
    mock_get_session.side_effect = generator
    
    mock_data_list = [Data(data="test1", username="user1"), Data(data="test2", username="user1")]
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_data_list
    
    mock_results = MagicMock()
    mock_results.scalars.return_value = mock_scalars
    session.execute.return_value = mock_results

    result = await get_read_data_async("user1")

    assert result == mock_data_list


@pytest.mark.asyncio
@patch("nodes.database_utils.get_async_session_node")
async def test_get_read_data_async_exception(mock_get_session, mock_db_session):
    generator, session = mock_db_session
    mock_get_session.side_effect = generator
    session.execute.side_effect = Exception("DB Error")

    result = await get_read_data_async("user1")

    assert result is False