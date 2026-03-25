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
    print("state.STATUS",state.STATUS,"ELECTION_IN_PROGRESS",state.ELECTION_IN_PROGRESS,"LAST_HEARDBEAT",time.time() - state.LAST_HEARTBEAT)
    if time.time() - state.LAST_HEARTBEAT > 15:
        state.ELECTION_IN_PROGRESS = False

    if state.STATUS != config.TYPE_STATUS_ACTIVE or state.ELECTION_IN_PROGRESS:
        return
    print(f"\n[Węzeł {config.NODE_ID}] Rozpoczynam elekcję!")

    node_list = state.ELECTION_MSGS.copy()
    if len(node_list) != 0:
        for node in node_list:
            send_message(config.TYPE_MSG_ELECTION, node)
    else:
        send_message(config.TYPE_MSG_ELECTION)
    state.ELECTION_IN_PROGRESS = True
    state.LEADER_ID = None
    state.ELECTION_MSGS.clear()


def heartbeat_worker():
    while True:
        time.sleep(2)
        if state.STATUS != config.TYPE_STATUS_ACTIVE: continue
        if len(state.ELECTION_MSGS.copy()) == 0 and state.ELECTION_IN_PROGRESS:
            state.ELECTION_IN_PROGRESS = False
            state.LEADER_ID = config.NODE_ID
            send_message(config.TYPE_MSG_COORDINATOR)
            print(f"\n[Węzeł {config.NODE_ID}] Jestem liderem!")

        if state.LEADER_ID == config.NODE_ID:
            send_message(config.TYPE_MSG_HEARTBEAT)
            state.LAST_HEARTBEAT = time.time()
        elif not state.ELECTION_IN_PROGRESS or time.time() - state.LAST_HEARTBEAT > 10:
            if time.time() - state.LAST_HEARTBEAT > 5:
                print("brak headbeat")
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

        if od == config.NODE_ID or (do and do != config.NODE_ID) or state.STATUS != config.TYPE_STATUS_ACTIVE:
            return

        if typ == config.TYPE_MSG_COORDINATOR:
            print(f"WEZEŁ{config.NODE_ID} od:{od}")
            if config.NODE_ID < od:
                state.ELECTION_IN_PROGRESS = False
                state.LEADER_ID = od
                state.LAST_HEARTBEAT = time.time()
            else:
                start_election()

        if config.NODE_ID < od: state.ELECTION_MSGS.add(od)

        if typ == config.TYPE_DATA_NEW:
            dane, user = msg.get("data"), msg.get("user")
            task_id, client_id = msg.get("task_id"), msg.get("client_id")

            #print(dane,user,client_id,task_id)
            try:
                nowe_dane = Data(data=dane,username=user)
                dane_to_user = add_data_to_db_sync(nowe_dane)
                #print("id: ", dane_to_user)
                if dane_to_user is not False:
                    #print("wysyłam")
                    new_record_dict = dane_to_user.model_dump()
                    send_message(config.TYPE_DATA_OK, node_id=od, data=new_record_dict, task_id=task_id, client_id=client_id)
                else:
                    raise Exception("Błąd zapisu!")
            except Exception as e:
                print(e)
                send_message(config.TYPE_DATA_FAIL, od, task_id=task_id, client_id=client_id)

        elif typ == config.TYPE_DATA_DELETE:
            dane, user = msg.get("data"), msg.get("user")
            task_id, client_id = msg.get("task_id"), msg.get("client_id")

            #print(dane, user, client_id, task_id)
            try:
                data_id = delete_data_from_db_sync(data_id=dane, username=user)
                if data_id is not False:
                    send_message(config.TYPE_DATA_OK_DELETE, od, data=data_id ,task_id=task_id, client_id=client_id)
                else:
                    raise Exception("Brak danych!")
            except Exception as e:
                send_message(config.TYPE_DATA_FAIL, od, task_id=task_id, client_id=client_id)

        elif typ == config.TYPE_DATA_OK or typ == config.TYPE_DATA_OK_DELETE:
            t_id, c_id = msg.get("task_id"), msg.get("client_id")
            if c_id in state.REACT_CLIENTS:
                ws = state.REACT_CLIENTS[c_id]
                dane_to_user = msg.get("data")

                #print("id od węzła:",dane_to_user)
                type_send = "delete_from_list" if typ == config.TYPE_DATA_OK_DELETE else "add_to_list"

                async def notify():
                    await ws.send_json({"task_id": t_id, "status": "success", "message": "Lider wykonał zadanie!", "data": dane_to_user, "data_type": type_send})

                asyncio.run_coroutine_threadsafe(notify(), state.MAIN_LOOP)

        elif typ == config.TYPE_DATA_FAIL:
            t_id, c_id = msg.get("task_id"), msg.get("client_id")
            if c_id in state.REACT_CLIENTS:
                ws = state.REACT_CLIENTS[c_id]

                async def notify():
                    await ws.send_json({"task_id": t_id, "status": "error", "message": "Lider nie zapisał danych!"})

                asyncio.run_coroutine_threadsafe(notify(), state.MAIN_LOOP)

        elif typ == config.TYPE_MSG_ELECTION:
            state.ELECTION_IN_PROGRESS = True
            state.ELECTION_MSGS.clear()

            if config.NODE_ID > od: send_message(config.TYPE_MSG_OK, od)


        elif typ == config.TYPE_MSG_OK and config.NODE_ID > od:
            send_message(config.TYPE_MSG_OK, od)


        elif typ == config.TYPE_MSG_HEARTBEAT:
            print(f"WEZEŁ{config.NODE_ID} od:{od} -- HEARTBEAT")

            if config.NODE_ID > od:
                print("zaczynam ELEKCJE")
                start_election()
            elif state.LEADER_ID is None or state.LEADER_ID < od:
                state.LEADER_ID = od

            state.LAST_HEARTBEAT = time.time()

    channel.basic_consume(queue=result.method.queue, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()