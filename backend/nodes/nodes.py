import os
import subprocess
import sys

import requests
from fastapi import APIRouter, HTTPException,Depends

from models_user import User
from backend.auth import require_admin,get_current_user

from .state import nodes_db
NODES_KEY = os.getenv("NODES_KEY","KLUCZ_DO_WEZLOW!")

router = APIRouter(
    prefix="/nodes",
    tags=["Nodes"],
)

@router.get("/")
async def getALLNodes(user: User = Depends(get_current_user)):
    """Pobieramy wszystkie węzły"""
    active_nodes = []

    for node_id, info in nodes_db.items():
        # Sprawdzamy, czy okno terminala z procesem nadal fizycznie działa
        process = info["process"]
        is_running = process.poll() is None

        status = "RUNNING" if is_running else "STOPPED"

        active_nodes.append({
            "node_id": node_id,
            "port": info["port"],
            "url": f"http://127.0.0.1:{info['port']}",
            "status": status
        })

    return {"nodes": active_nodes}

@router.get("/{node_id}")
async def getNodeInfo(node_id: int,user: User = Depends(get_current_user)):
    if node_id not in nodes_db:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie istnieje!")

    port = nodes_db[node_id]["port"]
    url = nodes_db[node_id]["url"]+"/status"

    try:
        response = requests.get(url,timeout=2)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie odpowiada!")


@router.post("/deactivate/{node_id}")
async def deactivateNode(node_id: int,user:User = Depends(require_admin)):
    """Uprawnienia TYLKO super User"""

    if node_id not in nodes_db:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie istnieje!")

    port = nodes_db[node_id]["port"]
    url = nodes_db[node_id]["url"]+"/deactivate"

    try:
        response = requests.post(url,timeout=2)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie odpowiada!")

@router.post("/activate/{node_id}")
async def deactivateNode(node_id: int,user:User = Depends(require_admin)):
    if node_id not in nodes_db:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie istnieje!")

    port = nodes_db[node_id]["port"]
    url = nodes_db[node_id]["url"]+"/activate"
    headers = {"nodes-key": NODES_KEY}

    try:
        response = requests.post(url,headers=headers,timeout=2)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} nie odpowiada!")


@router.post("/{node_id}")
def create_node(node_id: int,user:User = Depends(require_admin)):
    """Uruchamia nowy węzeł"""
    if node_id in nodes_db and nodes_db[node_id]["process"].poll() is None:
        raise HTTPException(status_code=400, detail=f"Węzeł {node_id} już działa!")

    port = 8000 + node_id
    env = os.environ.copy()
    env["NODE_ID"] = str(node_id)

    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../nodes"))

    try:
        process = subprocess.Popen(
            ["cmd.exe", "/k", sys.executable, "-m", "uvicorn", "node_process:app", "--port", str(port)],
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=parent_dir
        )

        nodes_db[node_id] = {"port": port, "process": process, "url": "http://127.0.0.1:"+str(port)}
        return {"message": f"Utworzono Węzeł {node_id}!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd uruchamiania: {str(e)}")


@router.delete("/{node_id}")
def delete_node(node_id: int,user:User = Depends(require_admin)):
    """TYLKO ADMIN: Fizycznie zabija proces węzła"""
    if node_id not in nodes_db:
        raise HTTPException(status_code=404, detail=f"Węzeł {node_id} nie istnieje.")

    process = nodes_db[node_id]["process"]
    if process.poll() is None:
        try:
            #process.kill()
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], capture_output=True)
            del nodes_db[node_id]
            return {"message": f"Węzeł {node_id} zlikwidowany!"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Błąd: {str(e)}")
    else:
        del nodes_db[node_id]
        return {"message": "Węzeł był już wyłączony."}

