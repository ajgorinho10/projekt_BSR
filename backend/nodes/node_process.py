import asyncio, threading, uuid, json, requests, websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette import status
from contextlib import asynccontextmanager
import time

from nodes import config
from nodes import state

from .database_utils import add_data_to_db_async,delete_data_from_db_async,get_read_data_async
from .messaging import send_message
from .cluster_logic import rabbitmq_listener, heartbeat_worker
from database import init_db_node, Data

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uruchamia wątki odpowiedzialne ze komunikację procesu"""
    state.MAIN_LOOP = asyncio.get_running_loop()
    await init_db_node()
    threading.Thread(target=rabbitmq_listener, daemon=True).start()
    threading.Thread(target=heartbeat_worker, daemon=True).start()
    asyncio.create_task(connect_to_api())
    
    yield

app = FastAPI(title=f"Węzeł {config.NODE_ID}", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class KEYRestrictMiddleware(BaseHTTPMiddleware):
    """Middleware sprawdzający czy zapytanie posiada klucz dostępowy - """
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("nodes-key") != config.NODES_KEY and request.url.path not in ["/data"]:
            return JSONResponse(status_code=403, content={"detail": "Zabroniony"})
        return await call_next(request)


app.add_middleware(KEYRestrictMiddleware)


async def connect_to_api():
    """Łączy proces z główyn serwer zarządzającym"""
    uri = f"ws://127.0.0.1:8000/ws/nodes?api_key={config.NODES_KEY}"
    while True:
        last_send = None
        try:
            async with websockets.connect(uri) as ws:
                print("Connected -> API")
                while True:
                    data = {"leader_id": state.LEADER_ID, "node_id": config.NODE_ID, "status": state.STATUS}
                    if data != last_send:
                        await ws.send(
                            json.dumps({"leader_id": state.LEADER_ID, "node_id": config.NODE_ID, "status": state.STATUS}))
                        last_send = data
                        
                    closed_task = asyncio.create_task(ws.wait_closed())
                    done, pending = await asyncio.wait(
                        [closed_task],
                        timeout=2
                    )
                    if closed_task in done:
                        raise Exception("Połączenie WebSocket zostało przerwane przez serwer.")
                    
                    
        except Exception as e:
            print(e)
            last_send = None
            await asyncio.sleep(5)


@app.websocket("/ws/client")
async def websocket_client_endpoint(websocket: WebSocket):
    """Socket do komunikacji z użytkownikiem"""

    if state.STATUS == config.TYPE_STATUS_INACTIVE or state.ELECTION_IN_PROGRESS or state.LEADER_ID is None:
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
        return

    await websocket.accept()
    last_send_token = None
    username = None

    c_id = str(uuid.uuid4())
    state.REACT_CLIENTS[c_id] = websocket
    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            token, dane = payload.get("token"), payload.get("data")
            task_id = payload.get("task_id", str(uuid.uuid4()))
            action = payload.get("action")

            if last_send_token != token:
                res = requests.post(f"{config.API_ADDRESS}/nodes/verify-user?token={token}&api_key={config.NODES_KEY}")
                if res.status_code != 200:
                    await websocket.send_json({"error": "Auth failed"})
                    continue
                else:
                    last_send_token = token
                    username = res.json().get("username", "Unknown")


            if action == "get_data":
                await get_read_data(websocket, dane, username,task_id)

            elif config.NODE_ID == state.LEADER_ID:
                match action:
                    case "save_data":
                        await add_by_leader(websocket, dane, username, task_id)
                    case "delete_data":
                        await delete_by_leader(websocket, dane, username,task_id)

            else:
                match action:
                    case "save_data":
                        send_message(config.TYPE_DATA_NEW, state.LEADER_ID, dane, user=username, task_id=task_id, client_id=c_id)
                    case "delete_data":
                        send_message(config.TYPE_DATA_DELETE, state.LEADER_ID, dane, user=username, task_id=task_id, client_id=c_id)

    except WebSocketDisconnect:
        state.REACT_CLIENTS.pop(c_id, None)


@app.get("/status")
def get_status():
    """Zwraca status wątku"""
    return {"node_id": config.NODE_ID, "status": state.STATUS, "leader_id": state.LEADER_ID}

@app.post("/deactivate")
def deactivate_node():
    """Deaktywuje wątek"""
    state.LEADER_ID = None
    state.STATUS = config.TYPE_STATUS_INACTIVE
    return {"message":"Węzeł zatrzymany"}

@app.post("/activate")
def deactivate_node():
    """Aktywuje wątek"""
    state.STATUS = config.TYPE_STATUS_ACTIVE
    return {"message":"Węzeł zatrzymany"}

@app.post("/error-leader")
def make_error_leader():
    
    if config.NODE_ID == state.LEADER_ID:
        raise HTTPException(status_code=400, detail=f"Węzeł nie może być liderem!")
    
    print(f'Watek {config.NODE_ID} wykonuje błąd leader')
    threading.Thread(target=start_leader_error, daemon=True).start()
        
    return {"message":"Błąd wykonany!"}

@app.post("/error-spam")
def make_error_leader():
    
    if config.NODE_ID == state.LEADER_ID:
        raise HTTPException(status_code=400, detail=f"Węzeł nie może być liderem!")
    
    print(f'Watek {config.NODE_ID} wykonuje błąd spam')
    threading.Thread(target=start_spam_error, daemon=True).start()
        
    return {"message":"Błąd wykonany!"}

def start_leader_error():
    for i in range(0,5):
        print(f'[Węzeł {config.NODE_ID}] {i}: Send -> TYPE_MSG_COORDINATOR')
        send_message(config.TYPE_MSG_COORDINATOR)
        time.sleep(1)
        
def start_spam_error():
    for i in range(0, 32):
        print(f'[Węzeł {config.NODE_ID}] {i}: Send -> MSG')
        send_message("ERROR")


async def delete_by_leader(websocket,dane,username,task_id):
    """Usuwa rekord z bazy jako lider - odsyła informacje o statusie operacji do wątku zlecającego"""
    try:
        if await delete_data_from_db_async(dane,username):
            await websocket.send_json({"task_id": task_id, "status": "success", "message": "Usunięto (Lider)","data":dane,"data_type":"delete_from_list"})
        else:
            raise Exception("Brak danych!")
    except Exception:
        await websocket.send_json({"task_id": task_id, "status": "error", "message": "Błąd podczas usuwania (Lider)"})

async def add_by_leader(websocket,dane,username,task_id):
    """"Dodaje rekord z bazy jako lider - odsyła informacje o statusie operacji do wątku zlecającego"""
    try:
        data_from_db = await add_data_to_db_async(Data(data=dane, username=username))
        if data_from_db:
            print(f"Z bazy: {data_from_db} | TYP: {type(data_from_db)}")
            new_record_dict = data_from_db.model_dump()
            await websocket.send_json({"task_id": task_id, "status": "success", "message": "Zapisano (Lider)", "data": new_record_dict,"data_type":"add_to_list"})
        else:
            raise Exception("Błąd podczas zapisywania (Lider)!")
    except Exception as e:
        print(e)
        await websocket.send_json({"task_id": task_id, "status": "error", "message": "Błąd podczas zapisywania (Lider)"})

async def get_read_data(websocket,dane,username,task_id):
    """Odczytuje wszystkie rekordy użytkownika z bazy"""
    try:
        data = await get_read_data_async(username)
        data_to_send = [item.model_dump() for item in data]
        await websocket.send_json({"task_id": task_id, "status": "success", "message": "Pomyślnie pobrano dane", "data": data_to_send,"data_type":"new"})

    except Exception as e:
        print(e)
        await websocket.send_json(
            {"task_id": task_id, "status": "error", "message": "Błąd pobierania danych (Lider)"})