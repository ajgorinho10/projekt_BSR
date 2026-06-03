import pytest
import json
from unittest.mock import patch, AsyncMock
from nodes import state

@pytest.mark.asyncio
@patch("nodes.state.redis_client", new_callable=AsyncMock)
async def test_get_node(mock_redis):
    mock_redis.hget.return_value = '{"port": 8001, "pid": 123}'
    
    result = await state.get_node(1)
    
    mock_redis.hget.assert_called_with("nodes", 1)
    assert result == {"port": 8001, "pid": 123}

@pytest.mark.asyncio
@patch("nodes.state.redis_client", new_callable=AsyncMock)
async def test_add_nodes_db(mock_redis):
    data = {"port": 8002, "pid": 124}
    await state.add_nodes_db(2, data)
    mock_redis.hset.assert_called_with("nodes", 2, json.dumps(data))

@pytest.mark.asyncio
@patch("nodes.state.redis_client", new_callable=AsyncMock)
async def test_remove_nodes_db(mock_redis):
    await state.remove_nodes_db(1)
    mock_redis.hdel.assert_called_with("nodes", 1)