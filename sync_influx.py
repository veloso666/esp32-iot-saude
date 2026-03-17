#!/usr/bin/env python3
"""
InfluxDB Sync - IoT Saude Mestrado
Sincroniza dados faltantes entre dois InfluxDBs.
Roda via cron a cada 5 minutos em cada VM.

Uso: python3 sync_influx.py <IP_REMOTO>
"""

import sys
import logging
from influxdb import InfluxDBClient
from datetime import datetime

DB_NAME = "iot_medico"
MEASUREMENT = "metricas_iot"
SYNC_WINDOW = "2h"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("sync")

def get_points(client, label):
    query = f"SELECT * FROM {MEASUREMENT} WHERE time > now() - {SYNC_WINDOW}"
    try:
        result = client.query(query)
        points = list(result.get_points())
        log.info(f"{label}: {len(points)} pontos na janela de {SYNC_WINDOW}")
        return points
    except Exception as e:
        log.error(f"{label}: erro na consulta - {e}")
        return []

def points_to_timestamps(points):
    return {p["time"] for p in points}

def sync(remote_ip):
    log.info(f"Iniciando sync: remoto={remote_ip}")

    local = InfluxDBClient(host="localhost", port=8086, database=DB_NAME)
    try:
        remote = InfluxDBClient(host=remote_ip, port=8086, database=DB_NAME, timeout=10)
        remote.ping()
    except Exception as e:
        log.error(f"Remoto {remote_ip} indisponivel: {e}")
        return

    remote_points = get_points(remote, f"remoto({remote_ip})")
    if not remote_points:
        log.info("Nada para sincronizar")
        return

    local_points = get_points(local, "local")
    local_times = points_to_timestamps(local_points)

    missing = [p for p in remote_points if p["time"] not in local_times]
    log.info(f"Pontos faltantes no local: {len(missing)}")

    if not missing:
        log.info("Tudo sincronizado!")
        return

    tag_keys = {"protocolo", "dispositivo", "localizacao", "cloud"}
    batch = []
    for p in missing:
        tags = {k: v for k, v in p.items() if k in tag_keys and v is not None}
        fields = {k: v for k, v in p.items() if k not in tag_keys and k != "time" and v is not None}

        float_fields = {}
        for k, v in fields.items():
            try:
                float_fields[k] = float(v)
            except (ValueError, TypeError):
                float_fields[k] = v

        if float_fields:
            batch.append({
                "measurement": MEASUREMENT,
                "tags": tags,
                "time": p["time"],
                "fields": float_fields
            })

    if batch:
        CHUNK = 100
        written = 0
        for i in range(0, len(batch), CHUNK):
            chunk = batch[i:i+CHUNK]
            try:
                local.write_points(chunk, batch_size=CHUNK)
                written += len(chunk)
            except Exception as e:
                log.error(f"Erro no lote {i//CHUNK}: {e}")
        log.info(f"Sincronizados {written}/{len(batch)} pontos")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <IP_REMOTO>")
        sys.exit(1)
    sync(sys.argv[1])
