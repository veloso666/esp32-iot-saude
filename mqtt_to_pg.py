#!/usr/bin/env python3
"""MQTT -> PostgreSQL/TimescaleDB - IoT Saude Mestrado

Ingestor que assina o broker MQTT local e grava as mensagens na tabela
metricas_iot. Assina '#' para capturar tanto os topicos locais quanto os
prefixados (aws/, gcp/) que chegam pela bridge cross-cloud.
"""
import json, re, time
import paho.mqtt.client as mqtt
import psycopg2, psycopg2.extras

PG_DSN = "dbname=iot_medico user=iot password=iotmestrado host=localhost"
MQTT_TOPICS = [("#", 0)]  # inclui topicos locais e os prefixados (aws/, gcp/) vindos do bridge
_conn = None

def get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(PG_DSN)
        _conn.autocommit = True
    return _conn

def parse_line_protocol(payload):
    m = re.match(r'(\w+),(.+?) (.+)', payload)
    if not m:
        return None
    meas = m.group(1)
    tags = dict(i.split('=') for i in m.group(2).split(','))
    fields = {}
    for i in m.group(3).split(','):
        k, v = i.split('=')
        try:
            fields[k] = float(v)
        except ValueError:
            fields[k] = v
    return meas, tags, fields

def insert(meas, tags, fields):
    cur = get_conn().cursor()
    cur.execute(
        "INSERT INTO metricas_iot(measurement,protocolo,dispositivo,localizacao,cloud,fields)"
        " VALUES (%s,%s,%s,%s,%s,%s)",
        (meas, tags.get('protocolo'), tags.get('dispositivo'),
         tags.get('localizacao'), tags.get('cloud'), psycopg2.extras.Json(fields)))
    cur.close()

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] conectado rc={rc}", flush=True)
    for t, q in MQTT_TOPICS:
        client.subscribe(t, q)
        print(f"[MQTT] inscrito em {t}", flush=True)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        parsed = parse_line_protocol(payload)
        if parsed:
            meas, tags, fields = parsed
            if fields:
                insert(meas, tags, fields)
                print(f"[PG] {meas} <- {msg.topic} ({len(fields)} campos)", flush=True)
                return
        data = json.loads(payload)
        insert("sensores", {"topic": msg.topic},
               data if isinstance(data, dict) else {"value": data})
        print(f"[PG] json <- {msg.topic}", flush=True)
    except Exception as e:
        print(f"[ERRO] {e}", flush=True)

try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
except (AttributeError, TypeError):
    client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
print("=== IoT Saude - MQTT to PostgreSQL ===", flush=True)
while True:
    try:
        client.connect("localhost", 1883, 60)
        client.loop_forever()
    except Exception as e:
        print(f"[RECONECTA] {e}", flush=True)
        time.sleep(5)
