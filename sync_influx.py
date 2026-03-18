#!/usr/bin/env python3
"""
InfluxDB Sync - IoT Saude Mestrado
Sincroniza dados faltantes entre dois InfluxDBs.

Estrategia: detecta GAPS (periodos sem dados locais, ex: quando GCP
estava em falha) e preenche apenas esses gaps com dados do remoto.
Evita duplicatas verificando a contagem local antes de escrever.

Na GCP: python3 sync_influx.py 23.21.181.24
Na AWS: python3 sync_influx.py 136.115.185.214
"""

import sys
import logging
from datetime import datetime, timedelta
from influxdb import InfluxDBClient

DB_NAME = "iot_medico"
MEASUREMENT = "metricas_iot"
CHUNK = 50
GAP_THRESHOLD_S = 15

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


def get_first_time(client, label):
    try:
        result = client.query(f"SELECT * FROM {MEASUREMENT} ORDER BY time ASC LIMIT 1")
        points = list(result.get_points())
        if points:
            return points[0]["time"]
    except Exception as e:
        log.error(f"{label}: erro - {e}")
    return None


def get_count(client, since, until):
    query = f"SELECT count(temperatura) FROM {MEASUREMENT} WHERE time > '{since}' AND time <= '{until}'"
    try:
        result = client.query(query)
        points = list(result.get_points())
        if points:
            return points[0].get("count", 0)
    except:
        pass
    return 0


def find_gaps(client, since, until, interval_s=60):
    """Encontra periodos sem dados locais (gaps) varrendo janelas de tempo."""
    gaps = []
    cursor = datetime.fromisoformat(since.replace("Z", "+00:00"))
    end = datetime.fromisoformat(until.replace("Z", "+00:00"))
    gap_start = None

    while cursor < end:
        window_end = min(cursor + timedelta(seconds=interval_s), end)
        t1 = cursor.strftime("%Y-%m-%dT%H:%M:%SZ")
        t2 = window_end.strftime("%Y-%m-%dT%H:%M:%SZ")

        count = get_count(client, t1, t2)

        if count == 0:
            if gap_start is None:
                gap_start = t1
        else:
            if gap_start is not None:
                gaps.append((gap_start, t1))
                gap_start = None

        cursor = window_end

    if gap_start is not None:
        gaps.append((gap_start, end.strftime("%Y-%m-%dT%H:%M:%SZ")))

    return gaps


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
    first_local = get_first_time(local, "local")
    first_remote = get_first_time(remote, "remoto")

    if not last_remote:
        log.info("Remoto sem dados")
        return

    log.info(f"Local:  {first_local} -> {last_local or 'sem dados'}")
    log.info(f"Remoto: {first_remote} -> {last_remote}")

    if not last_local:
        cursor = "1970-01-01T00:00:00Z"
        alvo = last_remote
        log.info(f"Local vazio, copiando tudo de {cursor} ate {alvo}...")
        total = 0
        while True:
            points = fetch_points(remote, cursor, alvo)
            if not points:
                break
            written = write_points(local, points)
            total += written
            cursor = points[-1]["time"]
            log.info(f"  +{written} pontos (total: {total})")
            if cursor >= alvo:
                break
        log.info(f"=== Sync finalizado: {total} pontos copiados ===")
        return

    since = min(first_local, first_remote) if first_local and first_remote else first_local or first_remote
    until = last_remote

    if not since:
        log.info("Sem dados para sincronizar.")
        return

    log.info(f"Buscando gaps locais de {since} ate {until}...")
    gaps = find_gaps(local, since, until, interval_s=30)

    if not gaps:
        log.info("Nenhum gap encontrado. Dados consistentes.")
        return

    log.info(f"Encontrados {len(gaps)} gaps:")
    total = 0

    for i, (gap_start, gap_end) in enumerate(gaps):
        remote_count = get_count(remote, gap_start, gap_end)
        if remote_count == 0:
            continue

        log.info(f"  Gap {i+1}: {gap_start} -> {gap_end} ({remote_count} pontos no remoto)")

        cursor = gap_start
        while True:
            points = fetch_points(remote, cursor, gap_end)
            if not points:
                break
            written = write_points(local, points)
            total += written
            cursor = points[-1]["time"]
            if cursor >= gap_end:
                break

    log.info(f"=== Sync finalizado: {total} pontos preenchidos em {len(gaps)} gaps ===")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <IP_REMOTO>")
        print(f"  GCP: {sys.argv[0]} 23.21.181.24")
        print(f"  AWS: {sys.argv[0]} 136.115.185.214")
        sys.exit(1)
    sync(sys.argv[1])
