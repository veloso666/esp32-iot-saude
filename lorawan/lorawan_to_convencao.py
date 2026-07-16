#!/usr/bin/env python3
"""Adaptador LoRaWAN (ChirpStack) -> convencao MQTT do projeto.

Fluxo:
  ChirpStack publica uplinks decodificados em:
      application/<appId>/device/<devEui>/event/up   (JSON)
  Este servico assina esses topicos, extrai metricas (RSSI, SNR, fCnt->PDR,
  jitter, time-on-air->latencia, energia estimada + payload do sensor) e
  REPUBLICA em InfluxDB line protocol no topico:
      iot/lorawan/<dispositivo>/<localizacao>
  De onde o mqtt_to_pg.py (inscrito em '#') grava no PostgreSQL, no mesmo
  formato dos demais protocolos do DoE.

Roda na VM GCP (mesmo broker Mosquitto do ChirpStack).
"""
import json, math, time, base64
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
SUB_TOPIC = "application/+/device/+/event/up"
CLOUD = "gcp"
LOCALIZACAO = "UTI-01"

# Estimativa de energia: corrente media de TX do radio LoRa (mA @ 14 dBm).
TX_CURRENT_MA = 120.0

# Estado por dispositivo para PDR/jitter.
_state = {}  # devEui -> {"last_fcnt","recv","lost","last_ts","last_iat"}


def time_on_air_ms(sf, bw_hz, payload_len, cr=1, preamble=8, explicit_header=True, crc=True):
    """Time-on-air LoRa (ms) pela formula da Semtech."""
    try:
        tsym = (2 ** sf) / float(bw_hz)
        de = 1 if (bw_hz == 125000 and sf >= 11) else 0
        ih = 0 if explicit_header else 1
        crc_b = 1 if crc else 0
        num = 8 * payload_len - 4 * sf + 28 + 16 * crc_b - 20 * ih
        den = 4 * (sf - 2 * de)
        payload_symb = 8 + max(math.ceil(num / den) * (cr + 4), 0)
        t_preamble = (preamble + 4.25) * tsym
        t_payload = payload_symb * tsym
        return (t_preamble + t_payload) * 1000.0
    except Exception:
        return None


def on_connect(client, userdata, flags, rc):
    print(f"[LW] conectado rc={rc}", flush=True)
    client.subscribe(SUB_TOPIC, 0)
    print(f"[LW] inscrito em {SUB_TOPIC}", flush=True)


def on_message(client, userdata, msg):
    try:
        up = json.loads(msg.payload.decode("utf-8"))
        info = up.get("deviceInfo", {}) or {}
        dev = info.get("devEui") or info.get("deviceName") or "lora"
        dev_name = (info.get("deviceName") or dev).replace(" ", "_")

        obj = up.get("object", {}) or {}
        fcnt = up.get("fCnt", 0)

        rx = (up.get("rxInfo") or [{}])[0]
        rssi = rx.get("rssi")
        snr = rx.get("snr")

        tx = up.get("txInfo", {}) or {}
        lora = ((tx.get("modulation") or {}).get("lora") or {})
        sf = lora.get("spreadingFactor")
        bw = lora.get("bandwidth")  # Hz

        # tamanho do PHYPayload: 13 bytes de overhead + FRMPayload
        frm_len = 0
        if up.get("data"):
            try:
                frm_len = len(base64.b64decode(up["data"]))
            except Exception:
                frm_len = 0
        phy_len = 13 + frm_len

        lat = time_on_air_ms(sf, bw, phy_len) if (sf and bw) else None

        now = time.time()
        st = _state.setdefault(dev, {"last_fcnt": None, "recv": 0, "lost": 0,
                                     "last_ts": None, "last_iat": None})
        jitter = None
        if st["last_ts"] is not None:
            iat = (now - st["last_ts"]) * 1000.0
            if st["last_iat"] is not None:
                jitter = abs(iat - st["last_iat"])
            st["last_iat"] = iat
        st["last_ts"] = now

        st["recv"] += 1
        if st["last_fcnt"] is not None and fcnt > st["last_fcnt"]:
            st["lost"] += max(0, fcnt - st["last_fcnt"] - 1)
        st["last_fcnt"] = fcnt
        total = st["recv"] + st["lost"]
        pdr = (st["recv"] / total) if total > 0 else 1.0

        energia = None
        if lat is not None:
            energia = TX_CURRENT_MA * (lat / 1000.0) / 3600.0  # mAh por TX

        # monta os campos (line protocol)
        fields = {"pdr": round(pdr, 4), "seq": fcnt}
        if lat is not None: fields["latencia_ms"] = round(lat, 2)
        if jitter is not None: fields["jitter_ms"] = round(jitter, 2)
        if rssi is not None: fields["rssi"] = rssi
        if snr is not None: fields["snr"] = snr
        if energia is not None: fields["energia_mah"] = round(energia, 5)
        for k in ("temperatura", "umidade", "bpm", "spo2", "redundancia"):
            if k in obj:
                fields[k] = obj[k]
        fields.setdefault("redundancia", 1)

        field_str = ",".join(f"{k}={v}" for k, v in fields.items())
        line = (f"metricas_iot,protocolo=lorawan,dispositivo={dev_name},"
                f"localizacao={LOCALIZACAO},cloud={CLOUD} {field_str}")
        out_topic = f"iot/lorawan/{dev_name}/{LOCALIZACAO}"
        client.publish(out_topic, line, qos=0)
        print(f"[LW] {dev_name} fCnt={fcnt} rssi={rssi} snr={snr} pdr={pdr:.3f} -> {out_topic}", flush=True)
    except Exception as e:
        print(f"[LW][ERRO] {e}", flush=True)


def main():
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except (AttributeError, TypeError):
        client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    print("=== Adaptador LoRaWAN (ChirpStack) -> convencao MQTT ===", flush=True)
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            client.loop_forever()
        except Exception as e:
            print(f"[LW][RECONECTA] {e}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
