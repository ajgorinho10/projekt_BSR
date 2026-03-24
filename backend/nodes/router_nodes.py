import asyncio
import os
import subprocess
import sys

import psutil
import requests
from fastapi import APIRouter, HTTPException, Depends, Query

from database import User
from auth import require_admin, get_current_user

from nodes import state
from websockets_nodes import verify_ws_token_and_role

from dotenv import load_dotenv

load_dotenv()
NODES_KEY = os.getenv("NODES_KEY","KLUCZ_DO_WEZLOW!")

router = APIRouter(
    prefix="/nodes",
    tags=["Nodes"],
)

@router.post("/verify-user")
async def check_user(
    token: str,
    api_key: str
):
    if api_key != NODES_KEY:
        raise HTTPException(status_code=401, detail="Błędy Klucz API!")

    user = await verify_ws_token_and_role(token,["user","admin"])

    if user is None:
        raise HTTPException(status_code=403, detail="Błędny token użytkownika!")

    return {"username":user}


@router.get("/")
async def getALLNodes(user: User = Depends(get_current_user)):
    """Pobieramy wszystkie węzły"""
    return {"nodes": state.get_nodes_connections}

@router.get("/{node_id}")
async def getNodeInfo(node_id: int,user: User = Depends(get_current_user)):
    node = await state.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie istnieje!")

    port = node["port"]
    url = node["url"]+"/status"
    headers = {"nodes-key": NODES_KEY}

    try:
        response = requests.get(url,headers=headers,timeout=2)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie odpowiada!")


@router.post("/deactivate/{node_id}")
async def deactivateNode(node_id: int,user:User = Depends(require_admin)):
    """Uprawnienia TYLKO super User"""
    node = await state.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie istnieje!")

    port = node["port"]
    url = node["url"]+"/deactivate"
    headers = {"nodes-key": NODES_KEY}

    try:
        response = requests.post(url,headers=headers,timeout=2)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie odpowiada!")

@router.post("/activate/{node_id}")
async def deactivateNode(node_id: int,user:User = Depends(require_admin)):

    node = await state.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie istnieje!")

    port = node["port"]
    url = node["url"]+"/activate"
    headers = {"nodes-key": NODES_KEY}

    try:
        response = requests.post(url,headers=headers,timeout=2)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie odpowiada!")


@router.post("/{node_id}")
async def create_node(node_id: int,user:User = Depends(require_admin)):
    """Uruchamia nowy węzeł"""
    node = await state.get_node(node_id)
    if node is not None:
        pid = node.get("pid")
        # Pytamy system operacyjny, czy proces o tym numerze PID nadal działa
        if pid and psutil.pid_exists(pid):
            raise HTTPException(status_code=400, detail=f"Węzeł {node_id} już działa!")

    port = 8000 + node_id
    env = os.environ.copy()
    env["NODE_ID"] = str(node_id)

    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),"../"))
    print(f"parent_dir: {parent_dir}")
    try:
        print(os.getcwd())
        process = subprocess.Popen(
            ["cmd.exe", "/k", sys.executable, "-m","uvicorn", "nodes.node_process:app", "--port", str(port)],
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=parent_dir,
        )

        node_data = {
            "port": port,
            "pid": process.pid,
            "url": f"http://127.0.0.1:{port}"
        }

        await state.add_nodes_db(node_id, node_data)
        return {"message": f"Utworzono Węzeł {node_id}!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd uruchamiania: {str(e)}")


@router.delete("/{node_id}")
async def delete_node(node_id: int,user:User = Depends(require_admin)):
    """TYLKO ADMIN: Fizycznie zabija proces węzła"""
    node = await state.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Węzeł {node_id} nie istnieje.")

    pid = node.get("pid")
    if pid and psutil.pid_exists(pid):
        try:
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], capture_output=True)
            await state.remove_nodes_db(node_id)
            await state.remove_nodes_details_db(node_id)

            return {"message": f"Węzeł {node_id} zlikwidowany!"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Błąd: {str(e)}")
    else:
        await state.remove_nodes_db(node_id)
        return {"message": "Węzeł był już wyłączony."}
