import time
import json
import pika
import asyncio

#from .config import *
from nodes import config
#from .state import *
from nodes import state

from .messaging import send_message
from .database_utils import add_data_to_db_sync,delete_data_from_db_sync
from database import Data


def start_election():
    if state.STATUS != "ACTIVE" or state.ELECTION_IN_PROGRESS:
        return
    print(f"\n[Węzeł {config.NODE_ID}] Rozpoczynam elekcję!")
    if len(state.ELECTION_MSGS) != 0:
        for node in state.ELECTION_MSGS:
            send_message(config.TYPE_MSG_ELECTION, node)
    else:
        send_message(config.TYPE_MSG_ELECTION)
    state.ELECTION_IN_PROGRESS = True
    state.LEADER_ID = None
    state.ELECTION_MSGS.clear()


def heartbeat_worker():
    while True:
        time.sleep(2)
        if state.STATUS != "ACTIVE": continue
        if len(state.ELECTION_MSGS) == 0 and state.ELECTION_IN_PROGRESS:
            state.ELECTION_IN_PROGRESS = False
            state.LEADER_ID = config.NODE_ID
            send_message(config.TYPE_MSG_COORDINATOR)
            print(f"\n[Węzeł {config.NODE_ID}] Jestem liderem!")

        if state.LEADER_ID == config.NODE_ID:
            send_message(config.TYPE_MSG_HEARTBEAT)
        elif not state.ELECTION_IN_PROGRESS:
            if time.time() - state.LAST_HEARTBEAT > 5.0 and time.time() - state.START_UP_TIME > 10:
                start_election()


def rabbitmq_listener():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='bully_cluster', exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(exchange='bully_cluster', queue=result.method.queue)

    def callback(ch, method, properties, body):
        msg = json.loads(body.decode())
        od = msg.get("od_wezla")
        typ = msg.get("typ")
        do = msg.get("do_wezla")

        if od == config.NODE_ID or (do and do != config.NODE_ID) or state.STATUS != "ACTIVE":
            return

        if config.NODE_ID < od: state.ELECTION_MSGS.add(od)

        if typ == config.TYPE_DATA_NEW:
            dane, user = msg.get("data"), msg.get("user")
            task_id, client_id = msg.get("task_id"), msg.get("client_id")

            print(dane,user,client_id,task_id)
            try:
                nowe_dane = Data(data=dane,username=user)
                if add_data_to_db_sync(nowe_dane):
                    send_message(config.TYPE_DATA_OK, od, task_id=task_id, client_id=client_id)
                else:
                    raise Exception("Błąd zapisu!")
            except Exception as e:
                send_message(config.TYPE_DATA_FAIL, od, task_id=task_id, client_id=client_id)

        elif typ == config.TYPE_DATA_DELETE:
            dane, user = msg.get("data"), msg.get("user")
            task_id, client_id = msg.get("task_id"), msg.get("client_id")

            print(dane, user, client_id, task_id)
            try:
                if delete_data_from_db_sync(data_id=dane, username=user):
                    send_message(config.TYPE_DATA_OK, od, task_id=task_id, client_id=client_id)
                else:
                    raise Exception("Brak danych!")
            except Exception as e:
                send_message(config.TYPE_DATA_FAIL, od, task_id=task_id, client_id=client_id)

        elif typ == config.TYPE_DATA_OK:
            t_id, c_id = msg.get("task_id"), msg.get("client_id")
            if c_id in state.REACT_CLIENTS:
                ws = state.REACT_CLIENTS[c_id]

                async def notify():
                    await ws.send_json({"task_id": t_id, "status": "success", "message": "Lider wykonał zadanie!"})

                asyncio.run_coroutine_threadsafe(notify(), state.MAIN_LOOP)

        elif typ == config.TYPE_DATA_FAIL:
            t_id, c_id = msg.get("task_id"), msg.get("client_id")
            if c_id in state.REACT_CLIENTS:
                ws = state.REACT_CLIENTS[c_id]

                async def notify():
                    await ws.send_json({"task_id": t_id, "status": "error", "message": "Lider nie zapisał danych!"})

                asyncio.run_coroutine_threadsafe(notify(), state.MAIN_LOOP)

        elif typ == config.TYPE_MSG_ELECTION and not state.ELECTION_IN_PROGRESS:
            state.ELECTION_IN_PROGRESS = True
            if config.NODE_ID > od: send_message(config.TYPE_MSG_OK, od)

        elif typ == config.TYPE_MSG_COORDINATOR:
            if config.NODE_ID < od:
                state.ELECTION_IN_PROGRESS = False
                state.LEADER_ID = od
                state.LAST_HEARTBEAT = time.time()

        elif typ == config.TYPE_MSG_HEARTBEAT:
            state.LAST_HEARTBEAT = time.time()
            if config.NODE_ID > od: start_election()

    channel.basic_consume(queue=result.method.queue, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()