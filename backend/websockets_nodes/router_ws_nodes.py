"Sockety dla wątków(do komunikacji z serwerem głównym) oraz użytkownika(aktualizacje statusu wątków)"

import os
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, WebSocketException
from starlette.websockets import WebSocketState
from starlette import status

from nodes.state import *
from .ws_utils import verify_ws_token_and_role

from dotenv import load_dotenv


load_dotenv()
NODES_KEY = os.getenv("NODES_KEY","KLUCZ_DO_WEZLOW!")

router = APIRouter(prefix="/ws", tags=["WebSockets"])


@router.websocket("/nodes")
async def websocket_nodes(websocket: WebSocket, api_key: str = Query(None)):
    """Socket do komunikacji między serwerem głównym a wątekiem - zabezpieczony kluczem "API_KEY" """
    if api_key != NODES_KEY:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    idN = None
    try:
        while True:
            data = await websocket.receive_json()
            print(data)
            #nodes_details_db[data["node_id"]] = data
            await add_nodes_details_db(data["node_id"],data)
            idN = data["node_id"]

    except WebSocketDisconnect as e:
        #nodes_details_db.pop(id)
        await remove_nodes_details_db(idN)
        pass

    except WebSocketException as e:
        #nodes_details_db.pop(id)
        await remove_nodes_details_db(idN)
        pass

    except Exception as e:
        await remove_nodes_details_db(idN)
        pass

@router.websocket("/")
async def websocket_frontend(websocket: WebSocket,token: str = Query(None)):
    """Socket dla użytkownika - zwraca aktualizację statu wątków"""
    try:
        await websocket.accept()

        user = await verify_ws_token_and_role(token, ["user", "admin"])
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        last_send_nodes = None
        last_send_info = None
        while True:
            if websocket.client_state != WebSocketState.CONNECTED:
                break

            nodes = await get_nodes_connections()
            info = await get_nodes_info()
            if last_send_nodes != nodes or last_send_info != info:
                data = {"nodes": nodes,"node_details": info}
                await websocket.send_json(data)
                last_send_nodes = nodes
                last_send_info = info

            await asyncio.sleep(1)

    except WebSocketDisconnect as e:
        print("Klient rozłączył się !")


    except RuntimeError as e:
        if "przerwał połączenie" in str(e) or "closed" in str(e):
            print("Klient gwałtownie przerwał połączenie.")
        else:
            print(f"Inny błąd wykonania: {e}")

    except Exception as e:
        pass