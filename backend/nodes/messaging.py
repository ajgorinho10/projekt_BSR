import pika
import json


#from .config import NODE_ID
from nodes import config
#from .state import STATUS
from nodes import state

def send_message(typ, node_id=None, data=None, user=None, task_id=None, client_id=None):
    if state.STATUS != "ACTIVE":
        return
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.exchange_declare(exchange='bully_cluster', exchange_type='fanout')

        wiadomosc = {"od_wezla": config.NODE_ID, "typ": typ}

        if node_id: wiadomosc["do_wezla"] = node_id
        if user: wiadomosc["user"] = user
        if data: wiadomosc["data"] = data
        if task_id: wiadomosc["task_id"] = task_id
        if client_id: wiadomosc["client_id"] = client_id

        channel.basic_publish(exchange='bully_cluster', routing_key='', body=json.dumps(wiadomosc))
        connection.close()
    except Exception as e:
        print(f"Błąd wysyłania: {e}")