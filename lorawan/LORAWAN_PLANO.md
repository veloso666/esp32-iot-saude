# LoRaWAN - Plano de Integracao ao Pipeline DoE

Setup: Gateway generico + no = modulo LoRaWAN Radioenge no UART/AT de um MCU (ESP32/Arduino)
+ Network Server = **ChirpStack self-hosted na GCP** (35.215.213.80). Regiao **AU915 sub-banda 2** (Brasil).

## Fluxo

```
[MCU + sensor] --UART/AT--> [Radioenge LoRaWAN] --RF 915MHz--> [Gateway]
      --(UDP 1700)--> [ChirpStack Gateway Bridge] --> [ChirpStack] --MQTT-->
      application/<app>/device/<devEui>/event/up
                          |
             lorawan_to_convencao.py  (decodifica + metricas)
                          |
             iot/lorawan/<dev>/<loc>  (line protocol)
                          |
             mqtt_to_pg.py --> PostgreSQL --> Grafana (card LoRaWAN)
```

---

## 1. Contrato de payload (uplink) - 7 bytes, big-endian

| byte | campo | tipo | descricao |
| --- | --- | --- | --- |
| 0 | seq | uint8 | contador local (wrap 0-255) |
| 1-2 | temperatura | int16 | valor x100 (ex.: 3660 = 36.60 C) |
| 3 | umidade | uint8 | % |
| 4 | bpm | uint8 | frequencia cardiaca |
| 5 | spo2 | uint8 | saturacao O2 % |
| 6 | redundancia | uint8 | 1 (sem) ou 2 (com) |

> O `seq` do payload e informativo; o **PDR/gaps** reais sao calculados pelo `fCnt` do LoRaWAN.

---

## 2. Decoder (ChirpStack v4 - Device Profile > Codec > JavaScript)

```javascript
function decodeUplink(input) {
  var b = input.bytes;
  var t = (b[1] << 8) | b[2];
  if (t > 32767) t -= 65536;
  return { data: {
    seq: b[0],
    temperatura: t / 100.0,
    umidade: b[3],
    bpm: b[4],
    spo2: b[5],
    redundancia: b[6]
  }};
}
```

---

## 3. Instalar ChirpStack v4 na GCP

> Requer a VM GCP ligada. Postgres, Redis e Mosquitto no mesmo host.

```bash
# Redis
sudo apt-get update -qq && sudo apt-get install -y redis-server

# Repo ChirpStack
sudo apt-get install -y apt-transport-https dirmngr
sudo mkdir -p /etc/apt/keyrings
sudo sh -c 'wget -qO- https://artifacts.chirpstack.io/packages/chirpstack.key | gpg --dearmor > /etc/apt/keyrings/chirpstack.gpg'
echo "deb [signed-by=/etc/apt/keyrings/chirpstack.gpg] https://artifacts.chirpstack.io/packages/4.x/deb stable main" | sudo tee /etc/apt/sources.list.d/chirpstack.list
sudo apt-get update -qq
sudo apt-get install -y chirpstack chirpstack-gateway-bridge

# Banco do ChirpStack
sudo -u postgres psql -c "CREATE ROLE chirpstack WITH LOGIN PASSWORD 'chirpstack';"
sudo -u postgres psql -c "CREATE DATABASE chirpstack WITH OWNER chirpstack;"
sudo -u postgres psql -d chirpstack -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# /etc/chirpstack/chirpstack.toml:
#   [postgresql] dsn="postgres://chirpstack:chirpstack@localhost/chirpstack?sslmode=disable"
#   [redis] servers=["redis://localhost/"]
#   [network] enabled_regions=["au915_2"]
#   [integration] enabled=["mqtt"]; [integration.mqtt] server="tcp://localhost:1883/"

# gateway-bridge: /etc/chirpstack-gateway-bridge/chirpstack-gateway-bridge.toml
#   [integration.mqtt] server="tcp://localhost:1883/"  (region au915_2, Semtech UDP :1700)

sudo systemctl enable --now chirpstack chirpstack-gateway-bridge
```

Web UI: `http://35.215.213.80:8080` (precisa liberar a porta 8080 no firewall).

---

## 4. Configurar o gateway

No painel do gateway (Dragino/RAK/etc.):
- **Modo**: Semtech Packet Forwarder (UDP) -> Server = `35.215.213.80`, porta **1700**.
  (ou Basics Station se preferir; ajustar o gateway-bridge.)
- **Regiao/Plano**: AU915, **canais 8-15 + 65** (sub-banda 2).
- No ChirpStack: **Gateways > Add** com o **Gateway EUI** (aparece no painel do gateway).

Confirmacao: no ChirpStack o gateway fica "seen" (online) e recebe stats.

---

## 5. Configurar o no (aplicacao + device)

No ChirpStack:
1. **Device Profile**: AU915 sub2, MAC 1.0.3 (comum na Radioenge), OTAA, cola o **codec** (secao 2).
2. **Application** "iot-saude" > **Add device** com o **DevEUI**.
3. Define **AppKey** (OTAA).
4. Anota DevEUI/AppEUI(JoinEUI)/AppKey para gravar no modulo.

---

## 6. MCU + modulo Radioenge (AT)

O MCU le o sensor, monta os 7 bytes e manda via AT para o modulo (OTAA, AU915).
Sequencia tipica (confirmar os comandos exatos no datasheet AT da Radioenge):

```
AT+DEUI=<DevEUI>
AT+APPEUI=<JoinEUI>
AT+APPKEY=<AppKey>
AT+CLASS=A
AT+CHMASK / AT+BAND -> AU915 sub-banda 2
AT+JOIN                      # OTAA
AT+SEND=<fport>:<hexpayload> # ex.: 2:0E4C4E5162 ...
```

> Os mnemonicos AT variam por firmware Radioenge - vou ajustar o sketch quando voce
> confirmar o modelo/manual. O payload segue o contrato da secao 1 (7 bytes).

---

## 7. Adaptador -> convencao (ja pronto)

`lorawan_to_convencao.py` assina `application/+/device/+/event/up`, calcula
RSSI, SNR, PDR (via fCnt), jitter (inter-arrival), latencia (time-on-air) e energia,
e republica em `iot/lorawan/<dev>/<loc>` (line protocol). Deploy:

```bash
sudo cp lorawan_to_convencao.py /root/lorawan_to_convencao.py
sudo tee /etc/systemd/system/lorawan-adapter.service >/dev/null <<'EOF'
[Unit]
Description=Adaptador LoRaWAN ChirpStack -> convencao MQTT
After=mosquitto.service chirpstack.service
Wants=mosquitto.service
[Service]
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 /root/lorawan_to_convencao.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable --now lorawan-adapter
```

---

## 8. Validacao

```bash
# ver uplinks crus do ChirpStack
mosquitto_sub -t 'application/#' -v
# ver a republicacao na convencao
mosquitto_sub -t 'iot/lorawan/#' -v
# conferir no banco
sudo -u postgres psql -d iot_medico -c \
  "SELECT count(*), avg((fields->>'rssi')::float) FROM metricas_iot WHERE protocolo='lorawan';"
```

O card **LoRaWAN** no dashboard DoE deixa de ser simulado e passa a mostrar dados reais.

---

## 9. Encaixe no DoE (Experimento B - 3x2)

- **Fator A = Tecnologia**: nivel LoRaWAN (vs WiFi, 6LoWPAN).
- **Fator B = Redundancia**: 1/2 (campo `redundancia` no payload).
- Metricas coletadas: latencia (ToA), jitter, PDR (fCnt), RSSI, SNR, energia.
- Rodar N replicas por combinacao, sob a mesma condicao de estresse (injecao de falhas),
  e comparar via ANOVA fatorial.

---

## PROVISIONADO NO CHIRPSTACK (16/07/2026)

Gateway e device criados via API (`chirpstack-api`). Gateway ja aparece ONLINE.

| Recurso | Valor |
| --- | --- |
| Tenant | ChirpStack (`eb73d80a-c381-4179-95aa-b7ca797dc2fc`) |
| Gateway | `rak7268-uti` / EUI `ac1f09fffe1c63bd` (RAK7268V2, AU915 sub2) |
| Application | `iot-saude` (`7ae38268-c7e3-457a-97f9-a2ea245f6e2f`) |
| Device profile | `saude-au915-otaa` (`12af7821-0c29-44b9-8415-ab7f31e0801e`) - AU915, LoRaWAN 1.0.3, RP002-1.0.3, OTAA, codec JS |
| Device | `no-uti-01` |

**Credenciais OTAA do no (gravadas no modulo Radioenge RD49C):**
```
DevEUI  = 0012f80000003bb8   (DevEUI REAL do modulo, lido via AT+DEUI=?)
AppKey  = 03ac61112108c8c446c139356326dcfc
JoinEUI = 0000000000000000
```

> O DevEUI antigo (`a15f964606e82507`) era inventado; o device foi recadastrado no
> ChirpStack com o DevEUI real via `prov_device.py`.

Gateway RAK7268: Work Mode = Packet Forwarder (Semtech UDP GWMP) -> 35.215.213.80:1700,
AU915 canais 8-15+65 (sub-banda 2). WAN via cabo ethernet no roteador (precisa internet).

## VALIDADO PONTA A PONTA (16/07/2026)

Modulo confirmado **LoRaWAN** (respondeu `AT+DEUI=?`; o `AT` puro nao e comando valido -
so `AT+<cmd>`, por isso a deteccao inicial deu falso-negativo).

Config gravada no modulo via AT (Serial Monitor 115200, line ending CR+LF):
```
AT+NJM=1
AT+CLASS=A
AT+APPEUI=00:00:00:00:00:00:00:00
AT+APPKEY=03:ac:61:11:21:08:c8:c4:46:c1:39:35:63:26:dc:fc
AT+CHMASK=ff00:0000:0000:0000:0002:0000   # AU915 sub2 (canais 9-16+66 na numeracao 1-based da Radioenge)
AT+ADR=1
AT+JOIN
```

> **IMPORTANTE**: depois de gravar o AppKey, **dar power-cycle no modulo** antes do
> `AT+JOIN`. Sem o reset a chave nova nao e aplicada e o join falha com `Invalid MIC`.

Resultado: `AT_JOIN_OK` -> ChirpStack logou JoinRequest + JoinAccept (dev_nonce validado),
uplinks `UnconfirmedDataUp` recebidos, adapter calculou rssi ~-48 dBm / snr ~13 / pdr 1.0,
e 3 linhas de `no-uti-01` (cloud=gcp) gravadas em `metricas_iot`. Pipeline completa OK.

---

## ESTADO ATUAL (16/07/2026) - servidor PRONTO

Instalado e rodando na GCP (35.215.213.80):
- **ChirpStack 4.19.0** (LNS) - regiao **au915_1 = AU915 sub-banda 2** (canais 8-15, 65) - UI em `:8080`
- **chirpstack-gateway-bridge 4.1.2** - Semtech UDP em **:1700** (topico `au915_1/gateway/...`)
- **Redis** + banco `chirpstack` no Postgres local
- **lorawan-adapter.service** ativo (assina `application/+/device/+/event/up`, republica no padrao)
- Firewall GCP: 8080/tcp e 1700/udp liberados
- `secret` do ChirpStack randomizado (openssl)

## Gateway confirmado: RAK 7268 (WisGateOS2, sem LTE)
SX1302, 8 canais, Network Server embutido + suporte a Packet Forwarder UDP / Basics Station / MQTT Bridge ChirpStack V4.
Usaremos como **packet forwarder apontando pro nosso ChirpStack** (nao o NS embutido).

### Config no WisGateOS2 (web UI do gateway)
1. **LoRa Network > Work Mode**: `Packet Forwarder` (Semtech UDP).
2. **Region/Frequency plan**: `AU915`, **sub-banda 2** (canais 8-15 + 65).
3. **Server address**: `35.215.213.80`  |  **Up/Down port**: `1700` / `1700`.
4. Anotar o **Gateway EUI** (LoRa > mostrado na UI) para registrar no ChirpStack.
5. Salvar/aplicar; o LED LoRa deve indicar trafego quando o no transmitir.

## Passos que faltam (seu lado)
1. **ChirpStack UI** `http://35.215.213.80:8080` (login `admin` / `admin` -> trocar senha):
   - Criar **Application** `iot-saude`.
   - Criar **Device Profile**: region `AU915`, MAC ver. `1.0.3` (OTAA), enable **Payload Codec = JavaScript** e colar o decoder (secao 3).
   - **Gateways > Add**: colar o **Gateway EUI** do RAK.
   - **Applications > iot-saude > Add device**: DevEUI + AppKey (OTAA).
2. **No (Radioenge + MCU)**: OTAA com o mesmo DevEUI/AppKey, enviar os 7 bytes (secao 1).
3. Validar 1o uplink (secao 8) - o card LoRaWAN passa a mostrar dados reais.

> Obs.: o `sim-sensor` ainda publica LoRaWAN simulado. Quando o no real entrar, me avise que
> eu desativo o protocolo lorawan do simulador pra nao misturar dado real com sintetico.
