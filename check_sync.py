#!/usr/bin/env python3
"""Verifica o estado de sincronizacao entre InfluxDB GCP e AWS."""
import urllib.request, json

GCP = "136.115.185.214"
AWS = "23.21.181.24"

def query(ip, q):
    url = f"http://{ip}:8086/query?db=iot_medico&q={q.replace(' ', '+')}"
    resp = urllib.request.urlopen(url, timeout=10)
    data = json.loads(resp.read().decode())
    results = data.get("results", [{}])[0]
    if "series" in results:
        return results["series"][0]["values"]
    return None

print("=" * 60)
print("  Verificacao de Sincronizacao InfluxDB")
print("=" * 60)

for name, ip in [("GCP", GCP), ("AWS", AWS)]:
    count = query(ip, "SELECT count(temperatura) FROM metricas_iot")
    last = query(ip, "SELECT * FROM metricas_iot ORDER BY time DESC LIMIT 1")

    total = count[0][1] if count else 0
    ultimo = last[0][0] if last else "N/A"

    print(f"\n  {name} ({ip}):")
    print(f"    Total de registros: {total}")
    print(f"    Ultimo registro:    {ultimo}")

# Comparar
count_gcp = query(GCP, "SELECT count(temperatura) FROM metricas_iot")
count_aws = query(AWS, "SELECT count(temperatura) FROM metricas_iot")

total_gcp = count_gcp[0][1] if count_gcp else 0
total_aws = count_aws[0][1] if count_aws else 0
diff = abs(total_gcp - total_aws)

print(f"\n{'=' * 60}")
print(f"  Diferenca: {diff} registros", end="")
if diff == 0:
    print(" (SINCRONIZADO)")
elif diff < 100:
    print(" (quase sincronizado - OK)")
else:
    print(f" (DESSINCRONIZADO - verificar sync_influx)")
print(f"  GCP: {total_gcp} | AWS: {total_aws}")
print(f"{'=' * 60}")
