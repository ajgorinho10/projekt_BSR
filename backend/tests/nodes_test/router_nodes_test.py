import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from nodes.router_nodes import router, NODES_KEY
from auth import require_admin, get_current_user

app = FastAPI()
app.include_router(router)

app.dependency_overrides[require_admin] = lambda: MagicMock()
app.dependency_overrides[get_current_user] = lambda: MagicMock()

client = TestClient(app)


# --- TESTY: /verify-user ---

def test_verify_user_invalid_api_key():
    """
    Weryfikuje: Odrzucenie weryfikacji przy błędnym kluczu API.
    Oczekiwane: Zwrócenie błędu 401 i komunikatu o błędnym kluczu.
    """
    response = client.post("/nodes/verify-user?token=test&api_key=bledny")
    assert response.status_code == 401
    assert response.json() == {"detail": "Błędy Klucz API!"}

@patch("nodes.router_nodes.verify_ws_token_and_role", new_callable=AsyncMock)
def test_verify_user_invalid_token(mock_verify):
    """
    Weryfikuje: Odrzucenie weryfikacji przy błędnym tokenie użytkownika.
    Oczekiwane: Zwrócenie błędu 403 po nieudanej weryfikacji przez funkcję pomocniczą.
    """
    mock_verify.return_value = None
    response = client.post(f"/nodes/verify-user?token=test&api_key={NODES_KEY}")
    assert response.status_code == 403

@patch("nodes.router_nodes.verify_ws_token_and_role", new_callable=AsyncMock)
def test_verify_user_success(mock_verify):
    """
    Weryfikuje: Poprawną weryfikację tokenu użytkownika.
    Oczekiwane: Zwrócenie kodu 200 oraz nazwy zautoryzowanego użytkownika.
    """
    mock_verify.return_value = "admin_user"
    response = client.post(f"/nodes/verify-user?token=test&api_key={NODES_KEY}")
    assert response.status_code == 200
    assert response.json() == {"username": "admin_user"}


# --- TESTY: / (Wszystkie węzły) ---

def test_get_all_nodes():
    """
    Weryfikuje: Pobieranie listy wszystkich węzłów.
    Oczekiwane: Zwrócenie kodu 200 oraz struktury zawierającej klucz "nodes".
    """
    response = client.get("/nodes/")
    assert response.status_code == 200
    assert "nodes" in response.json()


# --- TESTY: /{node_id} (Informacje o węźle) ---

@patch("nodes.router_nodes.state.get_node", new_callable=AsyncMock)
def test_get_node_info_not_found(mock_get_node):
    """
    Weryfikuje: Próbę pobrania informacji o nieistniejącym węźle w bazie.
    Oczekiwane: Zwrócenie błędu 400.
    """
    mock_get_node.return_value = None
    response = client.get("/nodes/99")
    assert response.status_code == 400

@patch("nodes.router_nodes.state.get_node", new_callable=AsyncMock)
@patch("nodes.router_nodes.requests.get")
def test_get_node_info_success(mock_requests_get, mock_get_node):
    """
    Weryfikuje: Poprawne pobranie statusu działającego węzła.
    Oczekiwane: Wykonanie zapytania HTTP GET bezpośrednio do węzła i zwrócenie jego statusu.
    """
    mock_get_node.return_value = {"port": 8001, "url": "http://127.0.0.1:8001"}
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ACTIVE"}
    mock_requests_get.return_value = mock_response

    response = client.get("/nodes/1")
    assert response.status_code == 200
    assert response.json() == {"status": "ACTIVE"}
    mock_requests_get.assert_called_once_with(
        "http://127.0.0.1:8001/status", headers={'nodes-key': NODES_KEY}, timeout=2
    )


# --- TESTY: Aktywacja / Deaktywacja ---

@patch("nodes.router_nodes.state.get_node", new_callable=AsyncMock)
@patch("nodes.router_nodes.requests.post")
def test_deactivate_node_success(mock_requests_post, mock_get_node):
    """
    Weryfikuje: Zlecenie wyłączenia węzła.
    Oczekiwane: Wysłanie żądania HTTP POST na lokalny endpoint /deactivate docelowego węzła i zwrócenie potwierdzenia.
    """
    mock_get_node.return_value = {"port": 8001, "url": "http://127.0.0.1:8001"}
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"message": "Zatrzymany"}
    mock_requests_post.return_value = mock_response

    response = client.post("/nodes/deactivate/1")
    assert response.status_code == 200
    mock_requests_post.assert_called_once_with(
        "http://127.0.0.1:8001/deactivate", headers={'nodes-key': NODES_KEY}, timeout=2
    )


# --- TESTY: Błędy (Error Injection) ---

@patch("nodes.router_nodes.state.get_node", new_callable=AsyncMock)
@patch("nodes.router_nodes.requests.post")
def test_make_error_leader_success(mock_requests_post, mock_get_node):
    """
    Weryfikuje: Zlecenie wywołania błędu lidera na konkretnym węźle.
    Oczekiwane: Wysłanie żądania HTTP POST na endpoint /error-leader docelowego węzła.
    """
    mock_get_node.return_value = {"port": 8001, "url": "http://127.0.0.1:8001"}
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "Success"}
    mock_requests_post.return_value = mock_response

    response = client.post("/nodes/error/leader/1")
    assert response.status_code == 200
    mock_requests_post.assert_called_once_with(
        "http://127.0.0.1:8001/error-leader", headers={'nodes-key': NODES_KEY}, timeout=2
    )

@patch("nodes.router_nodes.state.get_node", new_callable=AsyncMock)
def test_make_error_invalid_type_with_node(mock_get_node):
    """
    Weryfikuje: Próbę wywołania nieobsługiwanego typu błędu (innego niż leader/spam).
    Oczekiwane: Zwrócenie błędu 404 przez router zarządzający.
    """
    mock_get_node.return_value = {"port": 8001, "url": "http://127.0.0.1:8001"}
    response = client.post("/nodes/error/invalid/1")
    assert response.status_code == 404


# --- TESTY: Tworzenie węzła (Tworzenie procesu) ---

@patch("nodes.router_nodes.state.get_node", new_callable=AsyncMock)
@patch("nodes.router_nodes.psutil.pid_exists")
def test_create_node_already_running(mock_pid_exists, mock_get_node):
    """
    Weryfikuje: Próbę uruchomienia węzła, który ma już przypisany działający proces w systemie (PID).
    Oczekiwane: Zablokowanie operacji i zwrócenie błędu 400.
    """
    mock_get_node.return_value = {"pid": 1234}
    mock_pid_exists.return_value = True
    
    response = client.post("/nodes/1")
    assert response.status_code == 400
    assert "już działa" in response.json()["detail"]

@patch("nodes.router_nodes.state.get_node", new_callable=AsyncMock)
@patch("nodes.router_nodes.subprocess.Popen")
@patch("nodes.router_nodes.state.add_nodes_db", new_callable=AsyncMock)
@patch("nodes.router_nodes.platform.system")
def test_create_node_success_linux(mock_platform, mock_add_db, mock_popen, mock_get_node):
    """
    Weryfikuje: Pomyślne utworzenie procesu nowego węzła.
    Oczekiwane: Wywołanie komendy systemowej przez subprocess.Popen, zapisanie danych procesu do bazy w pamięci i kod 200.
    """
    mock_get_node.return_value = None
    mock_platform.return_value = "Linux"
    
    mock_process = MagicMock()
    mock_process.pid = 9999
    mock_popen.return_value = mock_process

    response = client.post("/nodes/2")
    assert response.status_code == 200
    assert response.json() == {"message": "Utworzono Węzeł 2!"}
    mock_popen.assert_called_once()
    mock_add_db.assert_called_once()


# --- TESTY: Usuwanie węzła (Zabijanie procesu) ---

@patch("nodes.router_nodes.state.get_node", new_callable=AsyncMock)
def test_delete_node_not_found(mock_get_node):
    """
    Weryfikuje: Próbę usunięcia nieistniejącego węzła.
    Oczekiwane: Zwrócenie błędu 404.
    """
    mock_get_node.return_value = None
    response = client.delete("/nodes/99")
    assert response.status_code == 404

@patch("nodes.router_nodes.state.get_node", new_callable=AsyncMock)
@patch("nodes.router_nodes.psutil.pid_exists")
@patch("nodes.router_nodes.state.remove_nodes_db", new_callable=AsyncMock)
def test_delete_node_already_stopped(mock_remove_db, mock_pid_exists, mock_get_node):
    """
    Weryfikuje: Usunięcie węzła, którego wpis istnieje w bazie, ale proces (PID) już nie działa w systemie.
    Oczekiwane: Wyczyszczenie wpisu w bazie danych bez zgłaszania błędów przez bibliotekę psutil.
    """
    mock_get_node.return_value = {"pid": 1234}
    mock_pid_exists.return_value = False
    
    response = client.delete("/nodes/1")
    assert response.status_code == 200
    mock_remove_db.assert_called_once_with(1)

@patch("nodes.router_nodes.state.get_node", new_callable=AsyncMock)
@patch("nodes.router_nodes.psutil.pid_exists")
@patch("nodes.router_nodes.psutil.Process")
@patch("nodes.router_nodes.state.remove_nodes_db", new_callable=AsyncMock)
@patch("nodes.router_nodes.state.remove_nodes_details_db", new_callable=AsyncMock)
def test_delete_node_success(mock_remove_details, mock_remove_db, mock_process, mock_pid_exists, mock_get_node):
    """
    Weryfikuje: Fizyczne zabicie procesu węzła i jego procesów potomnych.
    Oczekiwane: Wywołanie metody kill() na głównym procesie oraz jego dzieciach i usunięcie informacji o węźle z baz redis.
    """
    mock_get_node.return_value = {"pid": 1234}
    mock_pid_exists.return_value = True
    
    mock_parent = MagicMock()
    mock_child = MagicMock()
    mock_parent.children.return_value = [mock_child]
    mock_process.return_value = mock_parent

    response = client.delete("/nodes/2")
    
    assert response.status_code == 200
    assert response.json() == {"message": "Węzeł 2 zlikwidowany!"}
    
    mock_child.kill.assert_called_once()
    mock_parent.kill.assert_called_once()
    mock_remove_db.assert_called_once_with(2)
    mock_remove_details.assert_called_once_with(2)