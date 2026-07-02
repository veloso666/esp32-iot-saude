#!/bin/bash
set -e

echo "=========================================="
echo "  IoT Saude - Setup AWS EC2"
echo "  Mosquitto + InfluxDB + Grafana + Bridge"
echo "=========================================="

export DEBIAN_FRONTEND=noninteractive

echo "[1/5] Atualizando sistema..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

echo "[2/5] Instalando Mosquitto..."
sudo apt-get install -y -qq mosquitto mosquitto-clients

sudo tee /etc/mosquitto/conf.d/iot-saude.conf > /dev/null <<'MQTTCONF'
# IoT Saude Mestrado - Configuracao MQTT
listener 1883 0.0.0.0
allow_anonymous true
MQTTCONF

sudo systemctl enable mosquitto
sudo systemctl restart mosquitto
echo "[OK] Mosquitto rodando na porta 1883"

echo "[3/5] Instalando InfluxDB 1.8..."
curl -sL https://repos.influxdata.com/influxdata-archive_compat.key | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/influxdata.gpg
echo "deb [signed-by=/etc/apt/trusted.gpg.d/influxdata.gpg] https://repos.influxdata.com/debian stable main" | sudo tee /etc/apt/sources.list.d/influxdata.list
sudo apt-get update -qq
sudo apt-get install -y -qq influxdb
sudo systemctl enable influxdb
sudo systemctl start influxdb

sleep 2
influx -execute "CREATE DATABASE iot_medico"
echo "[OK] InfluxDB rodando na porta 8086, banco iot_medico criado"

echo "[4/5] Instalando Grafana..."
sudo apt-get install -y -qq apt-transport-https software-properties-common wget
sudo mkdir -p /etc/apt/keyrings/
wget -q -O - https://apt.grafana.com/gpg.key | gpg --dearmor | sudo tee /etc/apt/keyrings/grafana.gpg > /dev/null
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update -qq
sudo apt-get install -y -qq grafana
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
echo "[OK] Grafana rodando na porta 3000"

echo "[5/5] Instalando Python Bridge..."
sudo apt-get install -y -qq python3-pip
sudo pip3 install paho-mqtt influxdb

sudo tee /home/ubuntu/mqtt_to_influx.py > /dev/null <<'PYBRIDGE'
#!/usr/bin/env python3
"""
MQTT to InfluxDB Bridge - IoT Saude Mestrado
Recebe dados via MQTT e salva no InfluxDB
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
            tags_str = match.group(2)
            fields_str = match.group(3)
            tags = dict(item.split('=') for item in tags_str.split(','))
            fields = {}
            for item in fields_str.split(','):
                k, v = item.split('=')
                try:
                    fields[k] = float(v)
                except:
                    fields[k] = v
            return measurement, tags, fields
    except:
        pass
    return None, None, None

def on_connect(client, userdata, flags, rc):
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

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

print("=" * 50)
print("  IoT Saude Mestrado - MQTT to InfluxDB (AWS)")
print("=" * 50)

mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_forever()
PYBRIDGE

sudo tee /etc/systemd/system/mqtt-bridge.service > /dev/null <<'SVCFILE'
[Unit]
Description=MQTT to InfluxDB Bridge
After=mosquitto.service influxdb.service
Wants=mosquitto.service influxdb.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/ubuntu/mqtt_to_influx.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCFILE

sudo systemctl daemon-reload
sudo systemctl enable mqtt-bridge
sudo systemctl start mqtt-bridge
echo "[OK] Python Bridge rodando como servico systemd"

echo ""
echo "=========================================="
echo "  SETUP COMPLETO!"
echo "=========================================="
echo "  Mosquitto: porta 1883"
echo "  InfluxDB:  porta 8086 (banco: iot_medico)"
echo "  Grafana:   porta 3000 (admin/admin)"
echo "  Bridge:    mqtt-bridge.service"
echo "=========================================="
