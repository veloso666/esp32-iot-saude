# Avaliacao de Desempenho e Confiabilidade de Protocolos IoT no Contexto Medico

**Mestrado em Ciencia da Computacao - CIn/UFPE**
**Joao Lucas Veloso | Orientador: Prof. Eduardo Tavares | Coorientador: Thiago Valentim**

---

## Sobre o Projeto

Projeto de mestrado que avalia o **desempenho e a confiabilidade** da comunicacao de
tecnologias IoT (**WiFi, LoRaWAN, 6LoWPAN**) aplicadas ao monitoramento de saude, sobre
uma **arquitetura multi-cloud (GCP + AWS)**, usando **Design de Experimentos (DoE)** e
modelagem em **Redes de Petri Estocasticas (SPN)**.

> **Evolucao do projeto:** iniciou como um estudo de caso (ESP32 + WiFi + InfluxDB,
> apresentado em workshop). Foi reorganizado como um **projeto de experimentos (DoE)** e a
> infraestrutura migrou para **PostgreSQL + TimescaleDB** com **observabilidade (Prometheus)**
> e coleta de metricas de confiabilidade (MTBF/MTTR). Os arquivos da fase anterior ficam
> preservados em [`legacy/`](legacy/).

---

## Arquitetura atual (multi-cloud)

```
        Dispositivos IoT (WiFi / LoRaWAN / 6LoWPAN)
                        |
                    MQTT (1883)
                        |
        +---------------+----------------+
        |                                |
   [ GCP VM ]  <== bridge MQTT ==>  [ AWS VM ]
   Mosquitto                         Mosquitto
   mqtt_to_pg  (ingestor)            mqtt_to_pg
   PostgreSQL/TimescaleDB            PostgreSQL/TimescaleDB
   Grafana                           Grafana
   Prometheus + node/blackbox
   monitor-disp (MTBF/MTTR)
```

- **Replicacao cross-cloud** via bridge MQTT com prefixo de topico (`aws/`, `gcp/`),
  garantindo que cada mensagem apareca exatamente uma vez em cada banco (sem loop/duplicacao).
- **Persistencia**: PostgreSQL + TimescaleDB (substituiu o InfluxDB).
- **Observabilidade**: Prometheus + node_exporter + blackbox_exporter + Grafana.
- **Confiabilidade**: servico que registra transicoes UP/DOWN no banco (base para MTBF/MTTR/SPN).

### Infraestrutura Cloud (IPs estaticos)

| Servico | Descricao | GCP (35.215.213.80) | AWS (34.238.132.165) |
| --- | --- | --- | --- |
| Mosquitto | Broker MQTT + bridge | Porta 1883 | Porta 1883 |
| mqtt_to_pg | Ingestor MQTT -> PostgreSQL | Rodando | Rodando |
| PostgreSQL/TimescaleDB | Banco de series temporais | Porta 5432 | Porta 5432 |
| Grafana | Dashboards | Porta 3000 | Porta 3000 |
| Prometheus | Coleta de metricas | Porta 9090 (interna) | - |
| node/blackbox exporter | Metricas de sistema e probes | 9100 / 9115 | 9100 |

---

## Design de Experimentos (DoE)

**Experimento A** (artigo / estudo de caso): fatorial **2x2**
(Arquitetura x Injecao de falhas), com WiFi fixo - valida a metodologia e a arquitetura.

**Experimento B** (dissertacao): fatorial **3x2**
- **Fator A - Tecnologia de comunicacao**: WiFi, LoRaWAN, 6LoWPAN
- **Fator B - Redundancia**: 1 (sem) / 2 (com)
- Injecao de falhas = condicao de estresse constante
- Analise: **ANOVA fatorial** (efeitos de tecnologia, redundancia e interacao)
- Metricas de desempenho (latencia, jitter, PDR, energia, RSSI/SNR) e de confiabilidade
  (disponibilidade, tempo de failover/recuperacao, MTBF/MTTR)

A convencao de topicos/tags/metricas MQTT esta em [`CONVENCAO.md`](CONVENCAO.md).

---

## Camada de dados (PostgreSQL + TimescaleDB)

Banco **`iot_medico`** - usuario **`iot`** / senha **`iotmestrado`**.

- **`metricas_iot`** (hypertable): `time`, `protocolo`, `dispositivo`, `localizacao`,
  `cloud`, `fields` (jsonb com as metricas).
- **`eventos_disponibilidade`**: `servico`, `cloud`, `status` (UP/DOWN), `ts`,
  `dur_anterior_s` - base para MTBF/MTTR.

### Metricas de confiabilidade (SQL)

```sql
-- MTTR (tempo medio de reparo)
SELECT servico, round(avg(dur_anterior_s)::numeric,1) AS mttr_s
FROM eventos_disponibilidade
WHERE status='UP' AND dur_anterior_s IS NOT NULL GROUP BY servico;

-- MTTF (tempo medio ate falha)
SELECT servico, round(avg(dur_anterior_s)::numeric,1) AS mttf_s
FROM eventos_disponibilidade
WHERE status='DOWN' AND dur_anterior_s IS NOT NULL GROUP BY servico;
```

- **MTBF = MTTF + MTTR** · **Disponibilidade = MTTF / (MTTF + MTTR)**

---

## Dashboards (Grafana)

Plugin **HTML Graphics** (`gapit-htmlgraphics-panel`). JSONs provisionados em [`dashboards/`](dashboards/).

| Dashboard | UID | Conteudo |
| --- | --- | --- |
| Visao Executiva | `iot-exec` | banner + cards de servico + cards de tecnologia |
| DoE (Protocolos) | `iot-doe` | cards de tecnologia + graficos (latencia, PDR, jitter, RSSI) + tabela protocolo x redundancia |
| Infra & Observabilidade | `iot-infra` | disponibilidade, latencia cross-cloud, CPU/RAM/disco, eventos MTBF/MTTR |

Acesso: `http://35.215.213.80:3000` (GCP) e `http://34.238.132.165:3000` (AWS) - login `admin/admin`.

---

## Estrutura dos arquivos

```
esp32-iot-saude/
├── esp32-iot-saude.ino          # Firmware ESP32 (WiFi + metricas)
├── setup-pg.sh                  # Provisiona PostgreSQL + TimescaleDB + ingestor
├── mqtt_to_pg.py                # Ingestor MQTT -> PostgreSQL
├── sim_sensor.py                # Simulador dos 3 protocolos (valida pipeline sem hardware)
├── monitor_disponibilidade.py   # Registrador UP/DOWN (MTBF/MTTR)
├── CONVENCAO.md                 # Convencao de topicos/metricas + fatores do DoE
├── PROJETO_INFRA.md             # Documentacao completa da infraestrutura
├── pinagem.txt                  # Pinagem ESP32 + DHT22
├── gerar_diagramas.py           # Gera diagramas do artigo
├── gerar_graficos_analise.py    # Gera graficos de analise
├── dashboards/                  # JSONs dos dashboards Grafana
│   ├── dash-exec.json
│   ├── dash-doe.json
│   └── dash-infra.json
├── lorawan/                     # Integracao LoRaWAN (ChirpStack)
│   ├── no_lorawan_esp32.ino     #   No real: ESP32 + Radioenge -> 7 bytes -> AT+SENDB
│   ├── lorawan_to_convencao.py  #   Adapter ChirpStack -> convencao MQTT (metricas)
│   ├── prov_device.py           #   Provisiona o device no ChirpStack (API)
│   └── LORAWAN_PLANO.md         #   Plano + contrato de payload + credenciais OTAA
├── artigo/                      # Assets do artigo (diagramas, pseudocodigos)
├── dht_scan/                    # Utilitario: scanner de GPIOs para DHT22
└── legacy/                      # Fase anterior (InfluxDB / estudo de caso)
    ├── setup-aws.sh
    ├── mqtt_to_influx_aws.py
    ├── sync_influx.py
    ├── check_sync.py
    ├── setup_grafana.py
    ├── injetor_falhas.py
    ├── monitor_eventos.py
    └── monitor_eventos*.csv
```

---

## Como usar

### Provisionar uma VM (PostgreSQL + ingestor)

```bash
# PEER_IP = CIDR da nuvem parceira (ex.: 35.215.213.80/32)
sudo bash setup-pg.sh <PEER_IP>
```

### Validar o pipeline sem hardware (simulador)

```bash
# publica dados dos 3 protocolos a cada 5s (cloud = gcp|aws)
python3 sim_sensor.py gcp 5
```

### Coletar disponibilidade (MTBF/MTTR)

```bash
python3 monitor_disponibilidade.py   # requer Prometheus com probes blackbox
```

### Firmware ESP32 (WiFi)

1. Arduino IDE com suporte ESP32, bibliotecas `PubSubClient` e `DHT sensor library`.
2. Editar SSID/senha em `esp32-iot-saude.ino`, selecionar **ESP32 Dev Module** e fazer upload.
3. Serial Monitor a 115200 baud.

### LoRaWAN (no real - ChirpStack)

Servidor: **ChirpStack 4** self-hosted na GCP (AU915 sub-banda 2, OTAA, codec JS).
Gateway: **RAK 7268** em modo Packet Forwarder (Semtech UDP :1700).
No: **modulo Radioenge LoRaWAN (RD49C)** + ESP32 via UART/AT (GPIO16/17, 3V3).

1. Provisionar o device no ChirpStack: `python3 lorawan/prov_device.py`
   (usa o DevEUI real `0012F80000003BB8` + AppKey + JoinEUI).
2. Gravar `lorawan/no_lorawan_esp32.ino` no ESP32 - configura OTAA, faz o join e envia os
   7 bytes do contrato via `AT+SENDB`.
3. O servico `lorawan-adapter` (`lorawan/lorawan_to_convencao.py`) converte os uplinks do
   ChirpStack (RSSI/SNR/PDR/latencia/energia) para o padrao da convencao e grava no PostgreSQL.

> Validado ponta a ponta: join OTAA + uplinks reais gravando em `metricas_iot`.
> Contrato de payload, comandos AT e credenciais em [`lorawan/LORAWAN_PLANO.md`](lorawan/LORAWAN_PLANO.md).

---

## Proximos passos

- **6LoWPAN**: nRF52840 DK (border router) + no nRF52840 (SuperMini/XIAO).
- **LoRaWAN**: **funcionando** (modulo Radioenge + RAK7268 + ChirpStack) - ver [`lorawan/`](lorawan/).
  Falta trocar o `lerSensor()` do sketch pelo sensor clinico real (bpm/SpO2/temp).
- Substituir o simulador pelos dispositivos reais (mesma convencao MQTT).
- Rodar o **Experimento B (3x2)** e coletar as replicas para a ANOVA.
- Parametrizar o modelo **SPN** com os MTBF/MTTR medidos.
- (Opcional) Alertas persistidos, stack LGTM (Loki/Tempo/Mimir), Patroni para HA do PostgreSQL.

---

## Licenca

Projeto academico - Mestrado em Ciencia da Computacao, CIn/UFPE.
