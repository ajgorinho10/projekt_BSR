"""Główny proces wątku"""

import asyncio
import os
import subprocess
import sys
import platform

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
    """Umożliwa wątkom weryfikację użytkownika"""
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
    """Zwraca informacje o wybranym wątku"""
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
    """Tylko ADMIN - Wyłącza wątek"""
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
    """Tylko ADMIN - Włącza wątek"""
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
    """Tylko ADMIN - Uruchamia nowy węzeł"""
    node = await state.get_node(node_id)
    if node is not None:
        pid = node.get("pid")
        if pid and psutil.pid_exists(pid):
            raise HTTPException(status_code=400, detail=f"Węzeł {node_id} już działa!")

    port = 8000 + node_id
    env = os.environ.copy()
    env["NODE_ID"] = str(node_id)

    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),"../"))
    try:
        command = [sys.executable, "-m", "uvicorn", "nodes.node_process:app", "--port", str(port)]
        
        if platform.system() == "Windows":
            process = subprocess.Popen(
                ["cmd.exe", "/k"] + command,
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=parent_dir,
            )
        else:
            process = subprocess.Popen(
                command,
                env=env,
                cwd=parent_dir,
                start_new_session=True
            )

        node_data = {
            "port": port,
            "pid": process.pid,
            "url": f"http://127.0.0.1:{port}"
        }

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
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            
            await state.remove_nodes_db(node_id)
            await state.remove_nodes_details_db(node_id)

            return {"message": f"Węzeł {node_id} zlikwidowany!"}
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Błąd: {str(e)}")
            
    await state.remove_nodes_db(node_id)
    return {"message": "Węzeł był już wyłączony."}
