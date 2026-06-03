import pytest
import json
import time
from unittest.mock import patch, MagicMock

from nodes import config, state
from nodes.cluster_logic import (
    start_election, 
    heartbeat_worker, 
    rabbitmq_listener, 
    NUMBER_MSG_NODES, 
    TIME_MSG_NODES
)


@pytest.fixture(autouse=True)
def reset_globals():
    """Resetuje globalny stan aplikacji przed każdym uruchomieniem testu, zapobiegając wyciekom stanu między testami."""
    state.STATUS = config.TYPE_STATUS_ACTIVE
    state.ELECTION_IN_PROGRESS = False
    state.LEADER_ID = None
    state.LAST_HEARTBEAT = time.time()
    state.ELECTION_MSGS.clear()
    state.REACT_CLIENTS.clear()
    NUMBER_MSG_NODES.clear()
    TIME_MSG_NODES.clear()
    yield


@pytest.fixture
def rabbitmq_callback():
    """Uruchamia nasłuchiwanie na zmockowanym obiekcie połączenia RabbitMQ i wyciąga funkcję callback. Umożliwia to bezpośrednie testowanie logiki przetwarzania wiadomości bez konieczności stawiania prawdziwego brokera."""
    with patch("nodes.cluster_logic.pika.BlockingConnection") as mock_conn:
        mock_channel = MagicMock()
        mock_conn.return_value.channel.return_value = mock_channel
        mock_result = MagicMock()
        mock_result.method.queue = "test_queue"
        mock_channel.queue_declare.return_value = mock_result
        
        rabbitmq_listener()
        
        call_args = mock_channel.basic_consume.call_args
        return call_args.kwargs['on_message_callback']


# --- TESTY: start_election ---

@patch("nodes.cluster_logic.send_message")
def test_start_election_inactive(mock_send_message):
    """
    Weryfikuje: Zachowanie funkcji przy nieaktywnym węźle.
    Oczekiwane: Funkcja natychmiast przerywa działanie, węzeł nie wysyła żadnych komunikatów elekcyjnych.
    """
    state.STATUS = config.TYPE_STATUS_INACTIVE
    start_election()
    mock_send_message.assert_not_called()


@patch("nodes.cluster_logic.send_message")
def test_start_election_empty_msgs(mock_send_message):
    """
    Weryfikuje: Rozpoczęcie elekcji, gdy brakuje węzłów o wyższym priorytecie w pamięci podręcznej.
    Oczekiwane: Węzeł wysyła ogólną wiadomość ELECTION (broadcast) i oznacza status elekcji jako aktywny.
    """
    config.NODE_ID = 1
    start_election()
    mock_send_message.assert_called_with(config.TYPE_MSG_ELECTION)
    assert state.ELECTION_IN_PROGRESS is True


@patch("nodes.cluster_logic.send_message")
def test_start_election_with_target_nodes(mock_send_message):
    """
    Weryfikuje: Inicjację elekcji ze zidentyfikowanymi węzłami o wyższym ID.
    Oczekiwane: Węzeł wysyła pojedyncze komunikaty ELECTION celowane wyłącznie do węzłów ze zbioru ELECTION_MSGS.
    """
    config.NODE_ID = 1
    state.ELECTION_MSGS.update([2, 3])
    start_election()
    assert mock_send_message.call_count == 2
    assert state.ELECTION_IN_PROGRESS is True


# --- TESTY: heartbeat_worker ---

@patch("nodes.cluster_logic.time.sleep", side_effect=[None, InterruptedError])
@patch("nodes.cluster_logic.send_message")
def test_heartbeat_worker_as_leader(mock_send_message, mock_sleep):
    """
    Weryfikuje: Działanie wątku heartbeat, gdy dany węzeł pełni funkcję lidera.
    Oczekiwane: Lider cyklicznie rozsyła komunikat TYPE_MSG_HEARTBEAT do innych węzłów.
    """
    state.LEADER_ID = 5
    config.NODE_ID = 5
    
    with pytest.raises(InterruptedError):
        heartbeat_worker()
        
    mock_send_message.assert_called_with(config.TYPE_MSG_HEARTBEAT)


@patch("nodes.cluster_logic.time.sleep", side_effect=[None, InterruptedError])
@patch("nodes.cluster_logic.start_election")
def test_heartbeat_worker_timeout(mock_start_election, mock_sleep):
    """
    Weryfikuje: Detekcję awarii (timeout) aktualnego lidera przez węzeł podrzędny.
    Oczekiwane: Jeśli czas od ostatniego komunikatu heartbeat przekroczy limit, węzeł podrzędny inicjuje nową elekcję.
    """
    state.LEADER_ID = 2
    config.NODE_ID = 1
    state.LAST_HEARTBEAT = time.time() - 15  # Wymusza start elekcji
    
    with pytest.raises(InterruptedError):
        heartbeat_worker()
        
    mock_start_election.assert_called_once()


# --- TESTY: rabbitmq_listener (callback) ---

@patch("nodes.cluster_logic.requests.post")
def test_callback_spam_detection(mock_requests_post, rabbitmq_callback):
    """
    Weryfikuje: Reakcję lidera na zjawisko spamu (tzw. "Błąd spam").
    Oczekiwane: Po przekroczeniu 30 wiadomości w oknie czasowym poniżej 10 sekund, lider uderza w endpoint /deactivate atakującego węzła.
    """
    config.NODE_ID = 1
    state.LEADER_ID = 1
    
    # Warunki dla spamu
    NUMBER_MSG_NODES[2] = 30
    TIME_MSG_NODES[2] = time.time()
    
    msg = {"od_wezla": 2, "typ": "MSG"}
    rabbitmq_callback(None, None, None, json.dumps(msg).encode())
    
    mock_requests_post.assert_called_once()
    assert NUMBER_MSG_NODES[2] == 0


def test_callback_coordinator_msg(rabbitmq_callback):
    """
    Weryfikuje: Reakcję na ogłoszenie nowego lidera (komunikat COORDINATOR).
    Oczekiwane: Węzeł przerywa status elekcji i poprawnie zapisuje u siebie nowe ID koordynatora o ile posiada on wyższy priorytet.
    """
    config.NODE_ID = 1
    state.LEADER_ID = 3
    
    msg = {"od_wezla": 4, "typ": config.TYPE_MSG_COORDINATOR}
    rabbitmq_callback(None, None, None, json.dumps(msg).encode())
    
    assert state.LEADER_ID == 4
    assert state.ELECTION_IN_PROGRESS is False


@patch("nodes.cluster_logic.add_data_to_db_sync")
@patch("nodes.cluster_logic.send_message")
def test_callback_data_new_success(mock_send_message, mock_add_db, rabbitmq_callback):
    """
    Weryfikuje: Poprawny przepływ zapisu nowych danych zlecanych przez węzły podrzędne.
    Oczekiwane: Lider otrzymuje TYPE_DATA_NEW, dodaje rekord do bazy za pomocą funkcji synchronicznej i odsyła potwierdzenie TYPE_DATA_OK.
    """
    config.NODE_ID = 2
    
    mock_data = MagicMock()
    mock_data.model_dump.return_value = {"id": 1, "data": "test"}
    mock_add_db.return_value = mock_data
    
    msg = {"od_wezla": 1, "typ": config.TYPE_DATA_NEW, "data": "test", "user": "user1", "task_id": "t1", "client_id": "c1"}
    rabbitmq_callback(None, None, None, json.dumps(msg).encode())
    
    mock_add_db.assert_called_once()
    mock_send_message.assert_called_with(config.TYPE_DATA_OK, node_id=1, data={"id": 1, "data": "test"}, task_id="t1", client_id="c1")


@patch("nodes.cluster_logic.add_data_to_db_sync")
@patch("nodes.cluster_logic.send_message")
def test_callback_data_new_fail(mock_send_message, mock_add_db, rabbitmq_callback):
    """
    Weryfikuje: Obsługę błędu podczas zapisu zlecanych danych przez lidera.
    Oczekiwane: Jeśli funkcja bazodanowa zwróci False, lider wykrywa błąd i odsyła komunikat TYPE_DATA_FAIL do węzła zlecającego.
    """
    config.NODE_ID = 2
    mock_add_db.return_value = False  # Symulacja błędu DB
    
    msg = {"od_wezla": 1, "typ": config.TYPE_DATA_NEW, "data": "test", "user": "user1", "task_id": "t1", "client_id": "c1"}
    rabbitmq_callback(None, None, None, json.dumps(msg).encode())
    
    mock_send_message.assert_called_with(config.TYPE_DATA_FAIL, 1, task_id="t1", client_id="c1")


@patch("nodes.cluster_logic.asyncio.run_coroutine_threadsafe")
def test_callback_data_ok_websocket(mock_run_coroutine, rabbitmq_callback):
    """
    Weryfikuje: Kanał zwrotny od lidera do węzła zlecającego i powiadomienie końcowego klienta.
    Oczekiwane: Otrzymanie komunikatu DATA_OK aktywuje mechanizm WebSocket, powiadamiając asynchronicznie połączonego klienta.
    """
    state.MAIN_LOOP = MagicMock()
    ws_mock = MagicMock()
    state.REACT_CLIENTS["c1"] = ws_mock
    
    msg = {"od_wezla": 1, "typ": config.TYPE_DATA_OK, "task_id": "t1", "client_id": "c1", "data": {"id": 1}}
    rabbitmq_callback(None, None, None, json.dumps(msg).encode())
    
    mock_run_coroutine.assert_called_once()


@patch("nodes.cluster_logic.start_election")
def test_callback_heartbeat_from_lower_node(mock_start_election, rabbitmq_callback):
    """
    Weryfikuje: Ochronę spójności klastra (tzw. "Błąd lidera").
    Oczekiwane: Jeśli aktywny lider otrzyma komunikat HEARTBEAT od węzła o priorytecie niższym niż on sam (wystąpienie "split-brain"), natychmiast inicjuje nową elekcję.
    """
    config.NODE_ID = 5
    state.LEADER_ID = 5
    
    msg = {"od_wezla": 2, "typ": config.TYPE_MSG_HEARTBEAT}
    rabbitmq_callback(None, None, None, json.dumps(msg).encode())
    
    mock_start_election.assert_called_once()