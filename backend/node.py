import threading
import pika
import json
import os
import time
from fastapi import FastAPI
from pydantic import BaseModel

# --- KONFIGURACJA WĘZŁA ---
NODE_ID = int(os.getenv("NODE_ID", 1))
STATUS = "ACTIVE"
LEADER_ID = None
ELECTION_IN_PROGRESS = False
LAST_HEARTBEAT = time.time()

app = FastAPI(title=f"Węzeł {NODE_ID} - Bully Cluster")


def send_message(typ, do_wezla=None):
    if STATUS != "ACTIVE":
        return
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.exchange_declare(exchange='bully_cluster', exchange_type='fanout')

        wiadomosc = {"od_wezla": NODE_ID, "typ": typ}
        if do_wezla:
            wiadomosc["do_wezla"] = do_wezla

        channel.basic_publish(exchange='bully_cluster', routing_key='', body=json.dumps(wiadomosc))
        connection.close()
    except Exception as e:
        print(f"Błąd wysyłania: {e}")


# --- LOGIKA ALGORYTMU BULLY ---
def start_election():
    global ELECTION_IN_PROGRESS, LEADER_ID
    if STATUS != "ACTIVE": return

    if ELECTION_IN_PROGRESS:
        return

    ELECTION_IN_PROGRESS = True
    LEADER_ID = None
    print(f"\n[Węzeł {NODE_ID}] Rozpoczynam elekcję! Wysyłam ELECTION...")
    send_message("ELECTION")

    # Czekamy 2 sekundy. Jeśli nikt większy nam nie odpowie "OK", ogłaszamy się liderem.
    threading.Timer(2.0, check_election_results).start()


def check_election_results():
    global ELECTION_IN_PROGRESS, LEADER_ID
    # Jeśli flaga nadal jest True, to znaczy, że nikt silniejszy nas nie uciszył
    if ELECTION_IN_PROGRESS and STATUS == "ACTIVE":
        ELECTION_IN_PROGRESS = False
        LEADER_ID = NODE_ID
        print(f"\n🏆 [Węzeł {NODE_ID}] WYGRAŁEM WYBORY! Ogłaszam się KOORDYNATOREM (Liderem)!")
        send_message("COORDINATOR")


# --- NASŁUCHIWANIE RABBITMQ (Odbieranie wiadomości) ---
def rabbitmq_listener():
    global ELECTION_IN_PROGRESS, LEADER_ID, LAST_HEARTBEAT

    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='bully_cluster', exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='bully_cluster', queue=queue_name)

    def callback(ch, method, properties, body):
        global ELECTION_IN_PROGRESS, LEADER_ID, LAST_HEARTBEAT
        if STATUS != "ACTIVE":
            return

        msg = json.loads(body.decode())
        od = msg.get("od_wezla")
        typ = msg.get("typ")
        do = msg.get("do_wezla")

        if od == NODE_ID:
            return  # Ignorujemy własne echo

        if do and do != NODE_ID:
            return  # Ignorujemy wiadomości skierowane bezpośrednio do kogoś innego

        # REAKCJE NA KOMUNIKATY ALGORYTMU BULLY:
        if typ == "ELECTION":
            if NODE_ID > od:
                # Jestem większy! Uciszam mniejszego i sam robię wybory.
                print(f"[Węzeł {NODE_ID}] Otrzymałem ELECTION od {od}. Wysyłam mu OK i przejmuję inicjatywę.")
                send_message("OK", do_wezla=od)

                if LEADER_ID == NODE_ID:
                    print(f"[Węzeł {NODE_ID}] Przecież już jestem Liderem! Uciszam węzeł {od} komunikatem COORDINATOR.")
                    send_message("COORDINATOR")
                elif not ELECTION_IN_PROGRESS:
                    # Przejmuję inicjatywę tylko, jeśli nie trwają jeszcze moje wybory
                    start_election()

        elif typ == "OK":
            if ELECTION_IN_PROGRESS:
                print(f"[Węzeł {NODE_ID}] Dostałem OK od silniejszego węzła {od}. Wycofuję się z wyborów.")
                ELECTION_IN_PROGRESS = False

        elif typ == "COORDINATOR":
            LEADER_ID = od
            ELECTION_IN_PROGRESS = False
            LAST_HEARTBEAT = time.time()
            print(f"✅ [Węzeł {NODE_ID}] Zaakceptowałem nowego Lidera: Węzeł {LEADER_ID}")

        elif typ == "HEARTBEAT":
            if od == LEADER_ID:
                # Lider żyje, aktualizujemy stoper
                LAST_HEARTBEAT = time.time()

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()


# --- PĘTLA ŻYCIA (HEARTBEAT) ---
def lifecycle_loop():
    """Wątek działający w tle co 1 sekundę"""
    global LAST_HEARTBEAT
    while True:
        time.sleep(1)
        if STATUS != "ACTIVE":
            continue

        if LEADER_ID == NODE_ID:
            # Jestem Liderem - wysyłam sygnał życia do innych
            send_message("HEARTBEAT")
        elif not ELECTION_IN_PROGRESS:
            # Jestem Followerem - sprawdzam, czy Lider odzywał się w ciągu ostatnich 3.5 sekund
            if time.time() - LAST_HEARTBEAT > 3.5:
                print(f"\n[Węzeł {NODE_ID}] ⚠️ Brak sygnału od lidera {LEADER_ID}! Lider padł!")
                start_election()


# --- URUCHAMIANIE WĄTKÓW PRZY STARCIE ---
@app.on_event("startup")
def startup_event():
    threading.Thread(target=rabbitmq_listener, daemon=True).start()
    threading.Thread(target=lifecycle_loop, daemon=True).start()

    # Gdy węzeł wstaje, z automatu krzyczy, że chce sprawdzić, czy jest ktoś silniejszy
    time.sleep(1)  # małe opóźnienie na podłączenie do RabbitMQ
    start_election()


# --- ENDPOINTY (INTERFEJS DLA REACTA) ---
@app.get("/status")
def get_status():
    return {"node_id": NODE_ID, "status": STATUS, "leader_id": LEADER_ID}


@app.post("/crash")
def simulate_crash():
    """Symulacja potężnej awarii węzła (X spotkanie)"""
    global STATUS
    STATUS = "CRASHED"
    print(f"\n[Węzeł {NODE_ID}] 💥 AWARIA! Odcięto zasilanie i RabbitMQ.")
    return {"message": "Węzeł uległ awarii"}


@app.post("/recover")
def simulate_recovery():
    """Odzyskiwanie sprawności węzła (XII spotkanie)"""
    global STATUS
    STATUS = "ACTIVE"
    print(f"\n[Węzeł {NODE_ID}] 🔧 PRZYWRÓCONO DO ŻYCIA! Wracam do gry.")
    start_election()
    return {"message": "Węzeł przywrócony"}