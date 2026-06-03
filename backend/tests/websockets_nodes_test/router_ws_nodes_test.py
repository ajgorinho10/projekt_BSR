import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from unittest.mock import patch, AsyncMock

# 1. ZMIANA: Bezpośredni import właściwego modułu WebSocketów
# Jeśli plik leży w folderze websockets_nodes, użyj:
import websockets_nodes.router_ws_nodes as router_ws_nodes
from websockets_nodes.router_ws_nodes import router as ws_router

# Pozostałe importy
from nodes import NODES_KEY 

app = FastAPI()
app.include_router(ws_router) # 2. ZMIANA: Rejestracja routera WS
client = TestClient(app)

def test_ws_nodes_invalid_api_key():
    """Weryfikacja odrzucenia połączenia przy błędnym kluczu API"""
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/nodes?api_key=bledny_klucz"):
            pass
    assert exc.value.code in (1000, 1008)

# 3. ZMIANA: Użycie patch.object, które omija problem ze ścieżkami w postaci stringów
@patch.object(router_ws_nodes, "add_nodes_details_db", new_callable=AsyncMock)
@patch.object(router_ws_nodes, "remove_nodes_details_db", new_callable=AsyncMock)
def test_ws_nodes_valid_connection_and_disconnect(mock_remove, mock_add):
    """Weryfikacja poprawnego zapisu danych i usunięcia po rozłączeniu"""
    dane_testowe = {"node_id": 1, "status": "ACTIVE"}
    
    with client.websocket_connect(f"/ws/nodes?api_key={NODES_KEY}") as websocket:
        websocket.send_json(dane_testowe)
    
    mock_add.assert_called_with(1, dane_testowe)
    mock_remove.assert_called_with(1)

@patch.object(router_ws_nodes, "verify_ws_token_and_role", new_callable=AsyncMock)
def test_ws_frontend_invalid_token(mock_verify):
    """Weryfikacja odrzucenia użytkownika przy błędnym tokenie"""
    mock_verify.return_value = None  
    
    with client.websocket_connect("/ws/?token=bledny_token") as websocket:
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json() # Próba odczytu ujawni zamknięcie gniazda przez serwer
            
    assert exc.value.code in (1000, 1008)

@patch.object(router_ws_nodes, "verify_ws_token_and_role", new_callable=AsyncMock)
@patch.object(router_ws_nodes, "get_nodes_connections", new_callable=AsyncMock)
@patch.object(router_ws_nodes, "get_nodes_info", new_callable=AsyncMock)
def test_ws_frontend_valid_data_stream(mock_info, mock_connections, mock_verify):
    """Weryfikacja poprawnego odczytu stanu węzłów przez użytkownika"""
    mock_verify.return_value = "admin"
    mock_connections.return_value = [{"node_id": 2, "status": "RUNNING"}]
    mock_info.return_value = {"2": {"uptime": 120}}
    
    with client.websocket_connect("/ws/?token=poprawny_token") as websocket:
        response = websocket.receive_json()
        
        assert response == {
            "nodes": [{"node_id": 2, "status": "RUNNING"}],
            "node_details": {"2": {"uptime": 120}}
        }