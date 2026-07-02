#!/usr/bin/env python3
"""
MQTT to InfluxDB Bridge - IoT Saude Mestrado (AWS)
"""

import paho.mqtt.client as mqtt
from influxdb import InfluxDBClient
import json
import re
from datetime import datetime

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPICS = [
    ("iot-saude-mestrado/#", 0),
    ("hospital/#", 0)
]

INFLUX_HOST = "localhost"
INFLUX_PORT = 8086
INFLUX_DB = "iot_medico"

influx_client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT, database=INFLUX_DB)

def parse_line_protocol(payload):
    try:
        match = re.match(r'(\w+),(.+?) (.+)', payload)
        if match:
            measurement = match.group(1)
            tags = dict(item.split('=') for item in match.group(2).split(','))
            fields = {}
            for item in match.group(3).split(','):
                k, v = item.split('=')
                try:
                    fields[k] = float(v)
                except:
                    fields[k] = v
            return measurement, tags, fields
    except:
        pass
    return None, None, None

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[MQTT] Conectado! Codigo: {rc}")
    for topic, qos in MQTT_TOPICS:
        client.subscribe(topic, qos)
        print(f"[MQTT] Inscrito em: {topic}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        print(f"[MQTT] {msg.topic}: {payload[:100]}")
        measurement, tags, fields = parse_line_protocol(payload)
        if measurement and fields:
            json_body = [{
                "measurement": measurement,
                "tags": tags,
                "time": datetime.utcnow().isoformat() + "Z",
                "fields": fields
            }]
            influx_client.write_points(json_body)
            print(f"[InfluxDB] Salvo: {measurement} - {len(fields)} campos")
        else:
            try:
                data = json.loads(payload)
                json_body = [{
                    "measurement": "sensores",
                    "tags": {"topic": msg.topic},
                    "time": datetime.utcnow().isoformat() + "Z",
                    "fields": data if isinstance(data, dict) else {"value": data}
                }]
                influx_client.write_points(json_body)
                print(f"[InfluxDB] Salvo JSON: sensores")
            except:
                print(f"[AVISO] Formato nao reconhecido")
    except Exception as e:
        print(f"[ERRO] {e}")

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

print("=" * 50)
print("  IoT Saude Mestrado - MQTT to InfluxDB (AWS)")
print("=" * 50)

mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_forever()
