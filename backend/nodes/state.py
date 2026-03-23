import psutil
import redis.asyncio as redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

async def reset_database():
    await redis_client.delete("nodes_details")

    nodes_db = await redis_client.hgetall("nodes")
    for node_id, info_str in nodes_db.items():
        info = json.loads(info_str)
        pid = info.get("pid")

        if pid and psutil.pid_exists(pid):
            pass
        else:
            await remove_nodes_db(node_id)

async def get_node(idN):
    data = await redis_client.hget("nodes", idN)
    if data:
        return json.loads(data)
    return None

async def add_nodes_db(idN,dane):
    dane_json = json.dumps(dane)
    await redis_client.hset("nodes",idN,dane_json)

async def add_nodes_details_db(idN,dane):
    dane_json = json.dumps(dane)
    await redis_client.hset("nodes_details",idN,dane_json)

async def remove_nodes_db(idN):
    await redis_client.hdel("nodes",idN)

async def remove_nodes_details_db(idN):
    await redis_client.hdel("nodes_details",idN)


async def get_nodes_connections():
    active_nodes = []
    nodes_db = await redis_client.hgetall("nodes")

    for node_id, info_str in nodes_db.items():
        info = json.loads(info_str)
        pid = info.get("pid")

        is_running = False
        if pid and psutil.pid_exists(pid):
            is_running = True

        status = "RUNNING" if is_running else "STOPPED"

        active_nodes.append({
            "node_id": node_id,
            "port": info.get("port"),
            "url": info.get("url") or f"http://127.0.0.1:{info.get('port')}",
            "status": status
        })

    return active_nodes

async def get_nodes_info():
    active_nodes = {}
    nodes_details_db = await redis_client.hgetall("nodes_details")

    for node_id,info_str in nodes_details_db.items():
        active_nodes[node_id] = json.loads(info_str)

    return active_nodes
