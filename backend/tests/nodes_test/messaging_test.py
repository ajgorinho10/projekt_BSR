import json
from unittest.mock import patch, MagicMock
from nodes import messaging, state, config

@patch("nodes.messaging.pika.BlockingConnection")
def test_send_message_active_status(mock_pika):
    state.STATUS = "ACTIVE"
    config.NODE_ID = 1
    mock_conn = MagicMock()
    mock_channel = MagicMock()
    mock_conn.channel.return_value = mock_channel
    mock_pika.return_value = mock_conn

    messaging.send_message(config.TYPE_MSG_ELECTION, node_id=2, data={"test": 1})

    mock_channel.exchange_declare.assert_called_with(exchange='bully_cluster', exchange_type='fanout')
    
    # Weryfikacja argumentów wywołania
    call_args = mock_channel.basic_publish.call_args[1]
    assert call_args['exchange'] == 'bully_cluster'
    assert call_args['routing_key'] == ''
    
    body = json.loads(call_args['body'])
    assert body["od_wezla"] == 1
    assert body["typ"] == "ELECTION"
    assert body["do_wezla"] == 2
    assert body["data"] == {"test": 1}

@patch("nodes.messaging.pika.BlockingConnection")
def test_send_message_inactive_status(mock_pika):
    state.STATUS = "NOT_ACTIVE"
    messaging.send_message(config.TYPE_MSG_ELECTION)
    mock_pika.assert_not_called()