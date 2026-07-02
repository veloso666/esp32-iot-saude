#!/usr/bin/env python3
"""Registra transicoes de disponibilidade (UP/DOWN) no PostgreSQL para
analise de confiabilidade (MTBF/MTTR).

Le o Prometheus a cada POLL segundos (metrica probe_success dos probes
blackbox) e grava apenas as MUDANCAS de estado na tabela
eventos_disponibilidade, junto com a duracao do estado anterior.
"""
import time, json, urllib.request
import psycopg2

PG_DSN = "dbname=iot_medico user=iot password=iotmestrado host=localhost"
PROM = "http://localhost:9090/api/v1/query?query=probe_success"
POLL = 15

def get_states():
    with urllib.request.urlopen(PROM, timeout=10) as r:
        d = json.load(r)
    out = {}
    for res in d["data"]["result"]:
        serv = res["metric"].get("servico")
        if not serv:
            continue
        cloud = res["metric"].get("cloud")
        status = "UP" if res["value"][1] == "1" else "DOWN"
        out[serv] = (cloud, status)
    return out

def main():
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = True
    cur = conn.cursor()
    last, last_ts = {}, {}
    cur.execute("SELECT DISTINCT ON (servico) servico, status, extract(epoch from ts) "
                "FROM eventos_disponibilidade ORDER BY servico, ts DESC")
    for serv, status, ep in cur.fetchall():
        last[serv] = status
        last_ts[serv] = ep
    print("[MON] iniciado; estados:", last, flush=True)
    while True:
        try:
            states = get_states()
            now = time.time()
            for serv, (cloud, status) in states.items():
                if last.get(serv) != status:
                    dur = (now - last_ts[serv]) if serv in last_ts else None
                    cur.execute(
                        "INSERT INTO eventos_disponibilidade (servico, cloud, status, dur_anterior_s) "
                        "VALUES (%s,%s,%s,%s)", (serv, cloud, status, dur))
                    print(f"[MON] {serv} {last.get(serv)}->{status} dur={dur}", flush=True)
                    last[serv] = status
                    last_ts[serv] = now
        except Exception as e:
            print("[MON] erro:", e, flush=True)
        time.sleep(POLL)

if __name__ == "__main__":
    main()
