import threading
import pika
import json
import os
import time
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

#Komunikacja z menadżerem wątków
API_ADDRESS = os.getenv("API_ADDRESS","http://127.0.0.1:8000")
NODES_KEY = os.getenv("NODES_KEY","KLUCZ_DO_WEZLOW!")

# Konfiguracja węzła
NODE_ID = int(os.getenv("NODE_ID", 1))
STATUS = "ACTIVE"
LEADER_ID = None
ELECTION_IN_PROGRESS = False
LAST_HEARTBEAT = time.time()
START_UP_TIME = time.time()

# Typy wiadomości Algorytmu BULLY
TYPE_MSG_ELECTION = "ELECTION"
TYPE_MSG_OK = "OK"
TYPE_MSG_COORDINATOR = "COORDINATOR"
TYPE_MSG_HEARTBEAT = "HEARTBEAT"

# Zmienna zbiera wiadomości od węzłów podczas wyborów
ELECTION_MSGS = set()


app = FastAPI(title=f"Węzeł {NODE_ID}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[API_ADDRESS],
    allow_credentials=True,
    allow_methods=["GET, POST"],
    allow_headers=["*"],
)

''' Zabezpieczenie aby tylko api zarządzające miało dostęp do Węzłow '''
class KEYRestrictMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        key = request.headers.get("nodes-key")
        print(API_ADDRESS,NODES_KEY)
        print(key)

        if key != NODES_KEY:
            return JSONResponse(
                status_code=403,
                content={"detail": f"Dostęp zabroniony"}
            )

        response = await call_next(request)
        return response

app.add_middleware(KEYRestrictMiddleware)




def send_message(typ, node_id=None):
    if STATUS != "ACTIVE":
        return
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.exchange_declare(exchange='bully_cluster', exchange_type='fanout')

        wiadomosc = {"od_wezla": NODE_ID, "typ": typ}
        if node_id:
            wiadomosc["do_wezla"] = node_id

        channel.basic_publish(exchange='bully_cluster', routing_key='', body=json.dumps(wiadomosc))
        connection.close()
    except Exception as e:
        print(f"Błąd wysyłania: {e}")


def rabbitmq_listener():
    global ELECTION_IN_PROGRESS, LEADER_ID, LAST_HEARTBEAT, ELECTION_MSGS

    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='bully_cluster', exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='bully_cluster', queue=queue_name)

    def callback(ch, method, properties, body):
        global ELECTION_IN_PROGRESS, LEADER_ID, LAST_HEARTBEAT, ELECTION_MSGS
        if STATUS != "ACTIVE":
            return

        msg = json.loads(body.decode())
        od = msg.get("od_wezla")
        typ = msg.get("typ")
        do = msg.get("do_wezla")

        if od == NODE_ID or (do and do != NODE_ID):
            return

        if NODE_ID < od:
            ELECTION_MSGS.add(od)

        if typ == TYPE_MSG_ELECTION and ELECTION_IN_PROGRESS is False:
            ELECTION_IN_PROGRESS = True
            if NODE_ID > od:
                send_message(TYPE_MSG_OK, od)
                print(f"[Węzeł {NODE_ID}] Otrzymałem ELECTION od {od}. Wysyłam mu OK.")

        elif typ == TYPE_MSG_OK:
            if NODE_ID < od and LEADER_ID is None:
                print(f"[Węzeł {NODE_ID}] Dostałem OK od silniejszego węzła {od}. Czekam.")
            else:
                send_message(TYPE_MSG_OK, od)

        elif typ == TYPE_MSG_COORDINATOR:
            if NODE_ID < od:
                ELECTION_IN_PROGRESS = False
                ELECTION_MSGS.clear()
                LEADER_ID = od
                LAST_HEARTBEAT = time.time()
                print(f"[Węzeł {NODE_ID}] Zaakceptowałem nowego Lidera: Węzeł {LEADER_ID}")

        elif typ == TYPE_MSG_HEARTBEAT:
            LAST_HEARTBEAT = time.time()

            if NODE_ID > od:
                print(f"[Węzeł {NODE_ID}] Mniejszy węzeł {od} jest liderem! Rozpoczynam wybory!")
                start_election()

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()


def start_election():
    global ELECTION_IN_PROGRESS, LEADER_ID, ELECTION_MSGS

    if STATUS != "ACTIVE" or ELECTION_IN_PROGRESS:
        return

    print(f"\n[Węzeł {NODE_ID}] Rozpoczynam elekcję!")

    if len(ELECTION_MSGS) != 0:
        for node in ELECTION_MSGS:
            send_message(TYPE_MSG_ELECTION, node)
    else:
        send_message(TYPE_MSG_ELECTION)

    ELECTION_IN_PROGRESS = True
    LEADER_ID = None
    ELECTION_MSGS.clear()


def HEARTBEAT():
    global LAST_HEARTBEAT, ELECTION_MSGS, LEADER_ID, ELECTION_IN_PROGRESS
    while True:
        time.sleep(2)
        if STATUS != "ACTIVE":
            continue

        if len(ELECTION_MSGS) == 0 and ELECTION_IN_PROGRESS:
            ELECTION_IN_PROGRESS = False
            LEADER_ID = NODE_ID
            send_message(TYPE_MSG_COORDINATOR)
            print(f"\n [Węzeł {NODE_ID}] Jestem nowym liderem!")

        if LEADER_ID == NODE_ID:
            send_message(TYPE_MSG_HEARTBEAT)

        elif not ELECTION_IN_PROGRESS:
            if time.time() - LAST_HEARTBEAT > 5 and time.time() - START_UP_TIME > 10:
                print(f"\n[Węzeł {NODE_ID}] Brak sygnału od lidera! Inicjuję wybory!")
                start_election()
            elif LEADER_ID is None and len(ELECTION_MSGS) != 0:
                LEADER_ID = max(ELECTION_MSGS)


@app.on_event("startup")
def startup_event():
    global LAST_HEARTBEAT, START_UP_TIME
    threading.Thread(target=rabbitmq_listener, daemon=True).start()
    threading.Thread(target=HEARTBEAT, daemon=True).start()

    time.sleep(2)
    LAST_HEARTBEAT = time.time()
    START_UP_TIME = time.time()

# ENDPOINTY
@app.get("/status")
def get_status():
    return {"node_id": NODE_ID, "status": STATUS, "leader_id": LEADER_ID}


@app.post("/deactivate")
def deactivate_node():
    global STATUS
    STATUS = "NOT_ACTIVE"
    return {"node_id": NODE_ID, "status": STATUS}


@app.post("/activate")
def start_node():
    global STATUS, START_UP_TIME
    STATUS = "ACTIVE"
    START_UP_TIME = time.time()
    return {"node_id": NODE_ID, "status": STATUS}