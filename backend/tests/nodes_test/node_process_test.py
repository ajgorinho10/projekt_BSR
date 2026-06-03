import pytest
import json
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from unittest.mock import patch, AsyncMock, MagicMock

from nodes import config, state
from nodes.node_process import app, start_leader_error, start_spam_error

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_state():
    """Resetuje stan pamięci węzła przed każdym testem."""
    state.STATUS = config.TYPE_STATUS_ACTIVE
    state.LEADER_ID = 1
    state.ELECTION_IN_PROGRESS = False
    state.REACT_CLIENTS.clear()
    
    config.NODE_ID = 2
    config.NODES_KEY = "KLUCZ_TESTOWY"
    yield

# --- TESTY: Middleware ---

def test_middleware_invalid_key():
    """
    Weryfikuje: Odrzucenie żądania HTTP z nieprawidłowym kluczem API.
    Oczekiwane: Zwrócenie błędu 403 z komunikatem "Zabroniony".
    """
    response = client.get("/status", headers={"nodes-key": "BLEDNY_KLUCZ"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Zabroniony"}

def test_middleware_valid_key():
    """
    Weryfikuje: Akceptację żądania HTTP z prawidłowym kluczem API.
    Oczekiwane: Przepuszczenie żądania i zwrócenie statusu 200.
    """
    response = client.get("/status", headers={"nodes-key": config.NODES_KEY})
    assert response.status_code == 200

def test_middleware_bypass_for_data_path():
    """
    Weryfikuje: Wykluczenie ścieżki /data z autoryzacji kluczem w middleware.
    Oczekiwane: Brak błędu 403 (zwrócenie 404 ze względu na brak endpointu).
    """
    response = client.get("/data", headers={})
    assert response.status_code == 404 

# --- TESTY: API HTTP ---

def test_deactivate_node():
    """
    Weryfikuje: Proces deaktywacji węzła przez dedykowany endpoint.
    Oczekiwane: Zmiana statusu globalnego na INACTIVE i zresetowanie LEADER_ID.
    """
    response = client.post("/deactivate", headers={"nodes-key": config.NODES_KEY})
    assert response.status_code == 200
    assert state.STATUS == config.TYPE_STATUS_INACTIVE
    assert state.LEADER_ID is None

def test_activate_node():
    """
    Weryfikuje: Proces aktywacji uprzednio zdezaktywowanego węzła.
    Oczekiwane: Zmiana statusu globalnego z powrotem na ACTIVE.
    """
    client.post("/deactivate", headers={"nodes-key": config.NODES_KEY})
    response = client.post("/activate", headers={"nodes-key": config.NODES_KEY})
    assert response.status_code == 200
    assert state.STATUS == config.TYPE_STATUS_ACTIVE

@patch("nodes.node_process.threading.Thread")
def test_make_error_leader(mock_thread):
    """
    Weryfikuje: Inicjację błędu "leader error" na węźle podrzędnym.
    Oczekiwane: Uruchomienie logiki wprowadzającej błąd w osobnym wątku.
    """
    state.LEADER_ID = 1
    config.NODE_ID = 2
    response = client.post("/error-leader", headers={"nodes-key": config.NODES_KEY})
    assert response.status_code == 200
    mock_thread.assert_called_once()

def test_make_error_leader_is_leader():
    """
    Weryfikuje: Blokadę wykonania "leader error" na węźle, który aktualnie jest liderem.
    Oczekiwane: Zwrócenie błędu 400 z odpowiednim komunikatem.
    """
    state.LEADER_ID = 1
    config.NODE_ID = 1
    response = client.post("/error-leader", headers={"nodes-key": config.NODES_KEY})
    assert response.status_code == 400

@patch("nodes.node_process.threading.Thread")
def test_make_error_spam(mock_thread):
    """
    Weryfikuje: Inicjację ataku "spam error" na węźle.
    Oczekiwane: Uruchomienie logiki spamującej w osobnym wątku.
    """
    state.LEADER_ID = 1
    config.NODE_ID = 2
    response = client.post("/error-spam", headers={"nodes-key": config.NODES_KEY})
    assert response.status_code == 200
    mock_thread.assert_called_once()

# --- TESTY: Funkcje tła ---

@patch("nodes.node_process.time.sleep")
@patch("nodes.node_process.send_message")
def test_start_leader_error_execution(mock_send, mock_sleep):
    """
    Weryfikuje: Logikę działania funkcji generującej błąd lidera.
    Oczekiwane: Pięciokrotne wysłanie komunikatu TYPE_MSG_COORDINATOR z jednosekundowym opóźnieniem.
    """
    start_leader_error()
    assert mock_send.call_count == 5
    assert mock_sleep.call_count == 5

@patch("nodes.node_process.send_message")
def test_start_spam_error_execution(mock_send):
    """
    Weryfikuje: Logikę działania funkcji generującej atak spam.
    Oczekiwane: Szybkie wysłanie 32 bezcelowych komunikatów do innych węzłów.
    """
    start_spam_error()
    assert mock_send.call_count == 32

# --- TESTY: WebSockets (/ws/client) ---

def test_ws_client_rejected_when_inactive():
    """
    Weryfikuje: Próbę nawiązania połączenia WebSocket przez klienta z nieaktywnym węzłem.
    Oczekiwane: Natychmiastowe odrzucenie połączenia (kod 1013).
    """
    state.STATUS = config.TYPE_STATUS_INACTIVE
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/client"):
            pass
    assert exc.value.code in (1000, 1013)

@patch("nodes.node_process.requests.post")
def test_ws_client_auth_failure(mock_post):
    """
    Weryfikuje: Autoryzację tokenu klienta za pośrednictwem API głównego.
    Oczekiwane: Wysłanie komunikatu błędu, jeśli zewnętrzne API zwróci niepoprawny status autoryzacji.
    """
    mock_post.return_value.status_code = 401
    with client.websocket_connect("/ws/client") as ws:
        ws.send_json({"token": "bledny", "action": "get_data"})
        response = ws.receive_json()
        assert response == {"error": "Auth failed"}

@patch("nodes.node_process.requests.post")
@patch("nodes.node_process.get_read_data_async", new_callable=AsyncMock)
def test_ws_client_get_data(mock_get_db, mock_post):
    """
    Weryfikuje: Pobieranie danych przez połączonego klienta.
    Oczekiwane: Poprawne odpytanie bazy danych po udanej autoryzacji i zwrócenie ustrukturyzowanych wyników.
    """
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"username": "user1"}
    
    mock_item = MagicMock()
    mock_item.model_dump.return_value = {"id": 1, "data": "test_data"}
    mock_get_db.return_value = [mock_item]
    
    with client.websocket_connect("/ws/client") as ws:
        ws.send_json({"token": "poprawny", "action": "get_data"})
        response = ws.receive_json()
        assert response["status"] == "success"
        assert len(response["data"]) == 1
        assert response["data"][0]["data"] == "test_data"

@patch("nodes.node_process.requests.post")
@patch("nodes.node_process.add_data_to_db_async", new_callable=AsyncMock)
def test_ws_client_save_data_as_leader(mock_add_db, mock_post):
    """
    Weryfikuje: Zapis danych delegowany bezpośrednio do lidera klastra.
    Oczekiwane: Bezpośredni zapis do bazy z pominięciem kolejki wiadomości i zwrócenie potwierdzenia.
    """
    state.LEADER_ID = 2
    config.NODE_ID = 2
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"username": "user1"}
    
    mock_item = MagicMock()
    mock_item.model_dump.return_value = {"id": 1, "data": "new_data"}
    mock_add_db.return_value = mock_item
    
    with client.websocket_connect("/ws/client") as ws:
        ws.send_json({"token": "poprawny", "action": "save_data", "data": "new_data"})
        response = ws.receive_json()
        assert response["status"] == "success"
        assert response["data_type"] == "add_to_list"

@patch("nodes.node_process.requests.post")
@patch("nodes.node_process.delete_data_from_db_async", new_callable=AsyncMock)
def test_ws_client_delete_data_as_leader(mock_delete_db, mock_post):
    """
    Weryfikuje: Usunięcie danych delegowane bezpośrednio do lidera klastra.
    Oczekiwane: Wywołanie usunięcia w bazie i zwrócenie poprawnego komunikatu o usunięciu węzła.
    """
    state.LEADER_ID = 2
    config.NODE_ID = 2
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"username": "user1"}
    
    mock_delete_db.return_value = True
    
    with client.websocket_connect("/ws/client") as ws:
        ws.send_json({"token": "poprawny", "action": "delete_data", "data": 1})
        response = ws.receive_json()
        assert response["status"] == "success"
        assert response["data_type"] == "delete_from_list"

@patch("nodes.node_process.requests.post")
@patch("nodes.node_process.send_message")
def test_ws_client_save_data_as_follower(mock_send, mock_post):
    """
    Weryfikuje: Zapis danych przy połączeniu do węzła podrzędnego.
    Oczekiwane: Delegowanie zapisu do lidera za pomocą systemu RabbitMQ zamiast bezpośredniego zapisu do bazy.
    """
    state.LEADER_ID = 1
    config.NODE_ID = 2
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"username": "user1"}
    
    with client.websocket_connect("/ws/client") as ws:
        ws.send_json({"token": "poprawny", "action": "save_data", "data": "new_data"})
        
    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert args[0] == config.TYPE_DATA_NEW
    assert args[1] == 1