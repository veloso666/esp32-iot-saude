#!/usr/bin/env python3
"""
Simulador de sensores IoT medicos por tecnologia de enlace.
Publica em MQTT no padrao da CONVENCAO.md para validar o pipeline e os
dashboards ANTES do hardware real chegar (WiFi / LoRaWAN / 6LoWPAN).

Uso:
    python3 sim_sensor.py [cloud] [intervalo_seg]
Ex.: python3 sim_sensor.py gcp 5
"""
import sys
import time
import random
import paho.mqtt.client as mqtt

CLOUD = sys.argv[1] if len(sys.argv) > 1 else "gcp"
INTERVALO = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0

# Perfis realistas por tecnologia:
# lat (ms), jitter (ms), perda (prob), rssi (dBm), snr (dB), energia (mAh/msg)
PERFIS = {
    "wifi":    dict(lat=(5, 25),    jit=(0.5, 3),   perda=0.01, rssi=(-70, -40), snr=(0, 0),    ener=(0.7, 1.2)),
    "lorawan": dict(lat=(400, 1800), jit=(20, 120), perda=0.08, rssi=(-125, -80), snr=(-15, 10), ener=(0.02, 0.15)),
    "6lowpan": dict(lat=(15, 90),   jit=(2, 20),    perda=0.03, rssi=(-95, -60), snr=(0, 12),   ener=(0.1, 0.4)),
}

# Nos: (protocolo, dispositivo, localizacao, redundancia)
NOS = [
    ("wifi",    "esp32-uti01",    "UTI-01",        2),
    ("wifi",    "esp32-enf03",    "Enfermaria-03", 1),
    # lorawan agora vem do NO REAL (no-uti-01) via ChirpStack -> desativado no simulador
    ("6lowpan", "sixlo-uti02",    "UTI-02",        2),
    ("6lowpan", "sixlo-cc01",     "Centro-Cir-01", 1),
]

seqs = {n[1]: 0 for n in NOS}

def valor(faixa):
    return round(random.uniform(*faixa), 2)

def build(proto, disp, loc, red):
    p = PERFIS[proto]
    seqs[disp] += 1
    seq = seqs[disp]
    # PDR observado na janela (com leve efeito de redundancia)
    perda = p["perda"] * (0.4 if red == 2 else 1.0)
    pdr = round(max(0.0, 1.0 - random.uniform(0, perda * 2)), 4)
    lat = valor(p["lat"]) * (0.9 if red == 2 else 1.0)
    campos = {
        "seq": seq,
        "redundancia": red,
        "latencia_ms": round(lat, 2),
        "jitter_ms": valor(p["jit"]),
        "pdr": pdr,
        "rssi": valor(p["rssi"]),
        "snr": valor(p["snr"]),
        "energia_mah": valor(p["ener"]),
        "temperatura": round(random.uniform(35.5, 38.5), 2),
        "bpm": random.randint(60, 110),
        "spo2": random.randint(90, 100),
    }
    tags = f"protocolo={proto},dispositivo={disp},localizacao={loc},cloud={CLOUD}"
    fields = ",".join(f"{k}={v}" for k, v in campos.items())
    topico = f"iot-saude-mestrado/{proto}/{disp}"
    payload = f"metricas_iot,{tags} {fields}"
    return topico, payload, perda

def on_connect(c, u, f, rc):
    print(f"[SIM] conectado rc={rc} cloud={CLOUD} intervalo={INTERVALO}s", flush=True)

cli = None
try:
    cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
except (AttributeError, TypeError):
    cli = mqtt.Client()
cli.on_connect = on_connect
cli.connect("localhost", 1883, 60)
cli.loop_start()

print("=== Simulador de sensores (WiFi/LoRaWAN/6LoWPAN) ===", flush=True)
while True:
    for proto, disp, loc, red in NOS:
        topico, payload, perda = build(proto, disp, loc, red)
        # simula perda de pacote: as vezes nao publica
        if random.random() > perda:
            cli.publish(topico, payload, qos=0)
    time.sleep(INTERVALO)
