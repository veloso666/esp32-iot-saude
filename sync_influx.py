#!/usr/bin/env python3
"""
InfluxDB Sync - IoT Saude Mestrado
Sincroniza dados faltantes entre dois InfluxDBs.

Estrategia: pega o ultimo timestamp do remoto como ALVO fixo,
busca o ultimo timestamp local, e puxa apenas os pontos entre
o local e o alvo. Para quando alcanca o alvo.

Na GCP: python3 sync_influx.py 23.21.181.24
Na AWS: python3 sync_influx.py 136.115.185.214
"""

import sys
import logging
from influxdb import InfluxDBClient

DB_NAME = "iot_medico"
MEASUREMENT = "metricas_iot"
CHUNK = 50

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/var/log/sync_influx.log", mode="a"),
    ]
)
log = logging.getLogger("sync")
TAG_KEYS = {"protocolo", "dispositivo", "localizacao", "cloud"}

def get_last_time(client, label):
    try:
        result = client.query(f"SELECT * FROM {MEASUREMENT} ORDER BY time DESC LIMIT 1")
        points = list(result.get_points())
        if points:
            return points[0]["time"]
    except Exception as e:
        log.error(f"{label}: erro - {e}")
    return None

def fetch_points(client, since, until, limit=5000):
    query = f"SELECT * FROM {MEASUREMENT} WHERE time > '{since}' AND time <= '{until}' ORDER BY time ASC LIMIT {limit}"
    try:
        result = client.query(query)
        return list(result.get_points())
    except Exception as e:
        log.error(f"Erro buscar: {e}")
        return []

def write_points(client, points):
    batch = []
    for p in points:
        tags = {k: v for k, v in p.items() if k in TAG_KEYS and v is not None}
        fields = {}
        for k, v in p.items():
            if k in TAG_KEYS or k == "time" or v is None:
                continue
            try:
                fields[k] = float(v)
            except (ValueError, TypeError):
                fields[k] = v
        if fields:
            batch.append({
                "measurement": MEASUREMENT,
                "tags": tags,
                "time": p["time"],
                "fields": fields
            })

    written = 0
    for i in range(0, len(batch), CHUNK):
        try:
            client.write_points(batch[i:i+CHUNK], batch_size=CHUNK)
            written += len(batch[i:i+CHUNK])
        except Exception as e:
            log.error(f"Erro escrita: {e}")
    return written

def sync(remote_ip):
    log.info(f"=== Sync iniciado: remoto={remote_ip} ===")

    local = InfluxDBClient(host="localhost", port=8086, database=DB_NAME, timeout=15)
    try:
        remote = InfluxDBClient(host=remote_ip, port=8086, database=DB_NAME, timeout=15)
        remote.ping()
        log.info(f"Remoto {remote_ip} acessivel")
    except Exception as e:
        log.warning(f"Remoto {remote_ip} indisponivel: {e}")
        return

    last_local = get_last_time(local, "local")
    last_remote = get_last_time(remote, "remoto")

    if not last_remote:
        log.info("Remoto sem dados")
        return

    log.info(f"Local:  {last_local or 'sem dados'}")
    log.info(f"Remoto: {last_remote}")

    if last_local and last_local >= last_remote:
        log.info("Local ja esta atualizado. Nada a fazer.")
        return

    alvo = last_remote
    cursor = last_local or "1970-01-01T00:00:00Z"

    log.info(f"Sincronizando de {cursor} ate {alvo}...")

    total = 0
    while True:
        points = fetch_points(remote, cursor, alvo)
        if not points:
            break
        written = write_points(local, points)
        total += written
        cursor = points[-1]["time"]
        log.info(f"  +{written} pontos (total: {total}, cursor: {cursor})")

        if cursor >= alvo:
            break

    log.info(f"=== Sync finalizado: {total} pontos sincronizados ===")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <IP_REMOTO>")
        print(f"  GCP: {sys.argv[0]} 23.21.181.24")
        print(f"  AWS: {sys.argv[0]} 136.115.185.214")
        sys.exit(1)
    sync(sys.argv[1])
