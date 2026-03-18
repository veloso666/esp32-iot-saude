#!/usr/bin/env python3
"""Setup Grafana dashboards via API for both GCP and AWS."""
import json, urllib.request, urllib.error, base64

SERVERS = [
    {"name": "GCP", "ip": "136.115.185.214"},
    {"name": "AWS", "ip": "23.21.181.24"},
]

CREDS = base64.b64encode(b"admin:admin").decode()

def api(ip, path, method="GET", data=None):
    url = f"http://{ip}:3000/api{path}"
    headers = {
        "Authorization": f"Basic {CREDS}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  [ERRO] {method} {path}: {e.code} - {err[:200]}")
        return None

def get_datasource_uid(ip):
    ds_list = api(ip, "/datasources")
    if ds_list:
        for ds in ds_list:
            if ds.get("type") == "influxdb":
                return ds["uid"]
    return None

def build_dashboard(ds_uid):
    def panel(title, query, unit, panel_id, grid_x, grid_y, w=12, h=8, panel_type="timeseries"):
        p = {
            "id": panel_id,
            "title": title,
            "type": panel_type,
            "datasource": {"type": "influxdb", "uid": ds_uid},
            "targets": [{"refId": "A", "query": query, "rawQuery": True, "resultFormat": "time_series"}],
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "color": {"mode": "palette-classic"},
                    "custom": {
                        "lineWidth": 2,
                        "fillOpacity": 10,
                        "pointSize": 3,
                        "showPoints": "auto",
                    },
                },
                "overrides": [],
            },
            "gridPos": {"h": h, "w": w, "x": grid_x, "y": grid_y},
        }
        return p

    def stat_panel(title, query, unit, panel_id, grid_x, grid_y, w=6, h=4):
        return {
            "id": panel_id,
            "title": title,
            "type": "stat",
            "datasource": {"type": "influxdb", "uid": ds_uid},
            "targets": [{"refId": "A", "query": query, "rawQuery": True, "resultFormat": "time_series"}],
            "fieldConfig": {"defaults": {"unit": unit, "color": {"mode": "thresholds"}, "thresholds": {"steps": [{"color": "green", "value": None}]}}},
            "gridPos": {"h": h, "w": w, "x": grid_x, "y": grid_y},
        }

    row_y = 0
    panels = []

    # === ROW: Visao Geral ===
    panels.append({"id": 100, "title": "Visao Geral", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}, "collapsed": False})
    row_y += 1

    panels.append(stat_panel("Pacotes Enviados", "SELECT last(\"pacotes_enviados\") FROM \"metricas_iot\" WHERE $timeFilter", "short", 1, 0, row_y))
    panels.append(stat_panel("Pacotes Confirmados", "SELECT last(\"pacotes_confirmados\") FROM \"metricas_iot\" WHERE $timeFilter", "short", 2, 6, row_y))
    panels.append(stat_panel("Disponibilidade", "SELECT last(\"disponibilidade\") FROM \"metricas_iot\" WHERE $timeFilter", "percent", 3, 12, row_y))
    panels.append(stat_panel("Failovers", "SELECT last(\"failovers\") FROM \"metricas_iot\" WHERE $timeFilter", "short", 4, 18, row_y))
    row_y += 4

    # === ROW: Sensores ===
    panels.append({"id": 101, "title": "Sensores (DHT22 + Simulados)", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}, "collapsed": False})
    row_y += 1

    panels.append(panel("Temperatura (C)", "SELECT mean(\"temperatura\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "celsius", 10, 0, row_y))
    panels.append(panel("Umidade (%)", "SELECT mean(\"umidade\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "humidity", 11, 12, row_y))
    row_y += 8

    panels.append(panel("Frequencia Cardiaca (bpm)", "SELECT mean(\"freq_cardiaca\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "short", 12, 0, row_y))
    panels.append(panel("Saturacao O2 (%)", "SELECT mean(\"saturacao_o2\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "percent", 13, 12, row_y))
    row_y += 8

    # === ROW: Desempenho ===
    panels.append({"id": 102, "title": "Metricas de Desempenho", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}, "collapsed": False})
    row_y += 1

    panels.append(panel("Latencia MQTT (ms)", "SELECT mean(\"latencia\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "ms", 20, 0, row_y))
    panels.append(panel("Jitter (ms)", "SELECT mean(\"jitter\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "ms", 21, 12, row_y))
    row_y += 8

    panels.append(panel("RSSI WiFi (dBm)", "SELECT mean(\"rssi\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "dBm", 22, 0, row_y))
    panels.append(panel("Consumo Energetico (mA)", "SELECT mean(\"consumo_ma\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "short", 23, 12, row_y))
    row_y += 8

    panels.append(panel("PDR - Taxa de Entrega (%)",
        "SELECT (last(\"pacotes_confirmados\") / last(\"pacotes_enviados\")) * 100 FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)",
        "percent", 24, 0, row_y, w=24))
    row_y += 8

    # === ROW: Confiabilidade ===
    panels.append({"id": 103, "title": "Metricas de Confiabilidade", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}, "collapsed": False})
    row_y += 1

    panels.append(panel("Disponibilidade (%)", "SELECT mean(\"disponibilidade\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "percent", 30, 0, row_y))
    panels.append(panel("Failovers Acumulados", "SELECT max(\"failovers\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "short", 31, 12, row_y))
    row_y += 8

    panels.append(panel("Tempo de Failover (ms)", "SELECT max(\"tempo_failover\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "ms", 32, 0, row_y))
    panels.append(panel("Tempo de Recuperacao (ms)", "SELECT max(\"tempo_recuperacao\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "ms", 33, 12, row_y))
    row_y += 8

    # === ROW: Sucesso por Servidor ===
    panels.append({"id": 104, "title": "Taxa de Sucesso por Servidor", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}, "collapsed": False})
    row_y += 1

    panels.append(panel("Pacotes OK - GCP vs AWS",
        "SELECT last(\"ok_gcp\") AS \"GCP OK\", last(\"ok_aws\") AS \"AWS OK\" FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)",
        "short", 40, 0, row_y))
    panels.append(panel("Falhas - GCP vs AWS",
        "SELECT last(\"fail_gcp\") AS \"GCP Falhas\", last(\"fail_aws\") AS \"AWS Falhas\" FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)",
        "short", 41, 12, row_y))
    row_y += 8

    # === ROW: Sequencia ===
    panels.append({"id": 105, "title": "Controle de Sequencia", "type": "row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": row_y}, "collapsed": False})
    row_y += 1

    panels.append(panel("Numero Sequencial (seq)", "SELECT last(\"seq\") FROM \"metricas_iot\" WHERE $timeFilter GROUP BY time($__interval) fill(null)", "short", 50, 0, row_y, w=24))
    row_y += 8

    dashboard = {
        "dashboard": {
            "id": None,
            "uid": "iot-saude-mestrado",
            "title": "IoT Saude - Mestrado CIn/UFPE",
            "tags": ["iot", "mestrado", "saude"],
            "timezone": "browser",
            "refresh": "5s",
            "time": {"from": "now-30m", "to": "now"},
            "panels": panels,
            "schemaVersion": 39,
            "version": 0,
        },
        "overwrite": True,
    }
    return dashboard


def setup_server(server):
    ip = server["ip"]
    name = server["name"]
    print(f"\n{'='*50}")
    print(f"  Configurando Grafana - {name} ({ip})")
    print(f"{'='*50}")

    ds_uid = get_datasource_uid(ip)
    if not ds_uid:
        print(f"  [AVISO] Nenhum datasource InfluxDB encontrado. Criando...")
        ds_data = {
            "name": "InfluxDB",
            "type": "influxdb",
            "url": "http://localhost:8086",
            "database": "iot_medico",
            "access": "proxy",
            "isDefault": True,
        }
        result = api(ip, "/datasources", method="POST", data=ds_data)
        if result:
            ds_uid = result.get("datasource", {}).get("uid") or result.get("uid")
            print(f"  [OK] Datasource criado (uid={ds_uid})")
        else:
            print(f"  [ERRO] Nao foi possivel criar datasource")
            return
    else:
        print(f"  [OK] Datasource InfluxDB encontrado (uid={ds_uid})")

    dashboard = build_dashboard(ds_uid)
    result = api(ip, "/dashboards/db", method="POST", data=dashboard)
    if result:
        dash_url = result.get("url", "")
        print(f"  [OK] Dashboard criado/atualizado: http://{ip}:3000{dash_url}")
    else:
        print(f"  [ERRO] Falha ao criar dashboard")


if __name__ == "__main__":
    for srv in SERVERS:
        setup_server(srv)
    print(f"\n{'='*50}")
    print("  Grafana configurado em ambos os servidores!")
    print(f"{'='*50}")
