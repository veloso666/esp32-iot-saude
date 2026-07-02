#!/usr/bin/env python3
"""
InfluxDB Sync - IoT Saude Mestrado
Sincroniza dados faltantes entre dois InfluxDBs.

Estrategia: compara CONTAGENS por janela de tempo entre local e remoto.
Se o local tem significativamente menos dados que o remoto, copia os dados
faltantes. Usa timestamps originais do remoto para evitar duplicatas
(InfluxDB faz upsert por timestamp+tags).

Na GCP: python3 sync_influx.py 23.21.181.24
Na AWS: python3 sync_influx.py 136.115.185.214
"""

import sys
import logging
from datetime import datetime, timedelta
from influxdb import InfluxDBClient

DB_NAME = "iot_medico"
MEASUREMENT = "metricas_iot"
CHUNK = 500
WINDOW_S = 300
DEFICIT_RATIO = 0.8

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


def get_boundary(client, order="DESC"):
    try:
        result = client.query(f"SELECT * FROM {MEASUREMENT} ORDER BY time {order} LIMIT 1")
        points = list(result.get_points())
        if points:
            return points[0]["time"]
    except Exception as e:
        log.error(f"Erro boundary: {e}")
    return None


def get_count(client, since, until):
    q = f"SELECT count(temperatura) FROM {MEASUREMENT} WHERE time > '{since}' AND time <= '{until}'"
    try:
        result = client.query(q)
        points = list(result.get_points())
        if points:
            return points[0].get("count", 0)
    except:
        pass
    return 0


def find_deficits(local, remote, since, until, window_s=WINDOW_S):
    """Encontra janelas onde local tem menos dados que remoto."""
    deficits = []
    cursor = datetime.fromisoformat(since.replace("Z", "+00:00"))
    end = datetime.fromisoformat(until.replace("Z", "+00:00"))
    total_windows = 0
    deficit_windows = 0

    while cursor < end:
        window_end = min(cursor + timedelta(seconds=window_s), end)
        t1 = cursor.strftime("%Y-%m-%dT%H:%M:%SZ")
        t2 = window_end.strftime("%Y-%m-%dT%H:%M:%SZ")

        local_count = get_count(local, t1, t2)
        remote_count = get_count(remote, t1, t2)
        total_windows += 1

        if remote_count > 0 and local_count < remote_count * DEFICIT_RATIO:
            deficit = remote_count - local_count
            deficits.append((t1, t2, local_count, remote_count, deficit))
            deficit_windows += 1

        cursor = window_end

    log.info(f"Varridas {total_windows} janelas de {window_s}s, {deficit_windows} com deficit")
    return deficits


def fetch_points(client, since, until, limit=5000):
    q = f"SELECT * FROM {MEASUREMENT} WHERE time > '{since}' AND time <= '{until}' ORDER BY time ASC LIMIT {limit}"
    try:
        result = client.query(q)
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

    local = InfluxDBClient(host="localhost", port=8086, database=DB_NAME, timeout=30)
    try:
        remote = InfluxDBClient(host=remote_ip, port=8086, database=DB_NAME, timeout=30)
        remote.ping()
        log.info(f"Remoto {remote_ip} acessivel")
    except Exception as e:
        log.warning(f"Remoto {remote_ip} indisponivel: {e}")
        return

    first_local = get_boundary(local, "ASC")
    last_local = get_boundary(local, "DESC")
    first_remote = get_boundary(remote, "ASC")
    last_remote = get_boundary(remote, "DESC")

    if not last_remote:
        log.info("Remoto sem dados")
        return

    log.info(f"Local:  {first_local or 'vazio'} -> {last_local or 'vazio'}")
    log.info(f"Remoto: {first_remote} -> {last_remote}")

    if not last_local:
        log.info("Local vazio, copiando tudo...")
        cursor = "1970-01-01T00:00:00Z"
        total = 0
        while True:
            points = fetch_points(remote, cursor, last_remote)
            if not points:
                break
            written = write_points(local, points)
            total += written
            cursor = points[-1]["time"]
            log.info(f"  +{written} pontos (total: {total})")
            if cursor >= last_remote:
                break
        log.info(f"=== Sync: {total} pontos copiados ===")
        return

    since = min(first_local, first_remote) if first_local and first_remote else first_local or first_remote
    until = max(last_local, last_remote) if last_local and last_remote else last_remote

    log.info(f"Comparando local vs remoto de {since} ate {until}...")
    deficits = find_deficits(local, remote, since, until)

    if not deficits:
        log.info("Nenhum deficit encontrado. Dados consistentes.")
        return

    total_deficit = sum(d[4] for d in deficits)
    log.info(f"Encontrados {len(deficits)} janelas com deficit (~{total_deficit} pontos faltantes)")

    total_written = 0
    for i, (t1, t2, lc, rc, deficit) in enumerate(deficits):
        log.info(f"  [{i+1}/{len(deficits)}] {t1} -> {t2} (local:{lc} remoto:{rc} deficit:{deficit})")

        cursor = t1
        while True:
            points = fetch_points(remote, cursor, t2)
            if not points:
                break
            written = write_points(local, points)
            total_written += written
            cursor = points[-1]["time"]
            if cursor >= t2:
                break

    log.info(f"=== Sync finalizado: {total_written} pontos escritos de {len(deficits)} janelas ===")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <IP_REMOTO>")
        print(f"  GCP: {sys.argv[0]} 23.21.181.24")
        print(f"  AWS: {sys.argv[0]} 136.115.185.214")
        sys.exit(1)
    sync(sys.argv[1])
