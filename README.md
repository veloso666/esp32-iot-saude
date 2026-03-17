# IoT Saude - Monitoramento com ESP32 e MQTT

**Mestrado em Ciencia da Computacao - CIn/UFPE**
**Joao Lucas Veloso | Orientador: Prof. Eduardo Tavares | Coorientador: Thiago Valentim**

---

## Sobre o Projeto

Este projeto implementa uma arquitetura IoT para monitoramento de dados de saude em tempo real, com foco na **analise comparativa de protocolos de comunicacao** (WiFi, LoRaWAN) a partir de metricas de desempenho como **latencia, PDR (Packet Delivery Rate), RSSI e consumo energetico**.

A arquitetura utiliza um ESP32 com sensor DHT22 que coleta dados de temperatura e umidade, transmitindo via MQTT para uma infraestrutura em nuvem multi-cloud com failover automatico.

---

## Arquitetura

```
                                    ┌─────────────────────────────┐
                                    │     GOOGLE CLOUD PLATFORM   │
                                    │     34.69.204.126           │
  ┌──────────────┐    WiFi/MQTT     │  ┌───────────┐             │
  │  ESP32       │─────────────────>│  │ Mosquitto │             │
  │  DevKit-C V4 │    failover      │  │ Port 1883 │             │
  │  + DHT22     │─ ─ ─ ─ ─ ─ ─ ┐  │  └─────┬─────┘             │
  └──────────────┘               │  │        │                    │
    Metricas:                    │  │  ┌─────▼─────┐             │
    - Temperatura                │  │  │  Python   │             │
    - Umidade                    │  │  │  Bridge   │             │
    - Latencia                   │  │  └─────┬─────┘             │
    - PDR                        │  │        │                    │
    - RSSI                       │  │  ┌─────▼─────┐ ┌─────────┐│
    - Consumo                    │  │  │ InfluxDB  │ │ Grafana ││
                                 │  │  │ Port 8086 │ │ Port 3000││
                                 │  │  └───────────┘ └─────────┘│
                                 │  │         ▲                   │
                                 │  │         │ MQTT Bridge       │
                                 │  │         ▼                   │
                                 │  └─────────────────────────────┘
                                 │
                                 │  ┌─────────────────────────────┐
                                 │  │     AMAZON WEB SERVICES     │
                                 │  │     100.31.105.129          │
                                 └─>│  ┌───────────┐             │
                                    │  │ Mosquitto │             │
                                    │  │ Port 1883 │             │
                                    │  └─────┬─────┘             │
                                    │        │                    │
                                    │  ┌─────▼─────┐             │
                                    │  │  Python   │             │
                                    │  │  Bridge   │             │
                                    │  └─────┬─────┘             │
                                    │        │                    │
                                    │  ┌─────▼─────┐ ┌─────────┐│
                                    │  │ InfluxDB  │ │ Grafana ││
                                    │  │ Port 8086 │ │ Port 3000││
                                    │  └───────────┘ └─────────┘│
                                    └─────────────────────────────┘
```

---

## Componentes

### Camada de Sensores
| Componente | Descricao |
|---|---|
| **ESP32 DevKit-C V4** | Microcontrolador com WiFi integrado |
| **DHT22** | Sensor de temperatura e umidade |
| **GPIO4** | Pino de dados do DHT22 |

### Protocolo de Comunicacao
| Protocolo | Status |
|---|---|
| **WiFi 802.11** | Implementado |
| **LoRaWAN** | Futuro |
| **Sigfox / 6LoWPAN** | Futuro |

### Infraestrutura Cloud (Multi-Cloud)
| Servico | Descricao | GCP | AWS |
|---|---|---|---|
| **Mosquitto** | Broker MQTT | Porta 1883 | Porta 1883 |
| **Python Bridge** | MQTT to InfluxDB | Rodando | Rodando |
| **InfluxDB** | Time Series DB | Porta 8086 | Porta 8086 |
| **Grafana** | Dashboard | Porta 3000 | Porta 3000 |

---

## Metricas Coletadas

O ESP32 envia dados em **InfluxDB Line Protocol** via MQTT:

```
metricas_iot,protocolo=WiFi,dispositivo=ESP32_Real,localizacao=UTI-01,cloud=GCP
  temperatura=21.7,
  umidade=69.0,
  freq_cardiaca=77,       (simulado)
  saturacao_o2=97,        (simulado)
  rssi=-66,
  consumo_ma=160.0,
  latencia=23,
  pacotes_enviados=10928,
  pacotes_confirmados=10926,
  dht_simulado=0,
  failovers=2
```

| Metrica | Fonte | Descricao |
|---|---|---|
| `temperatura` | DHT22 (real) | Temperatura ambiente em Celsius |
| `umidade` | DHT22 (real) | Umidade relativa em % |
| `freq_cardiaca` | Simulado | Frequencia cardiaca (bpm) |
| `saturacao_o2` | Simulado | Saturacao de oxigenio (%) |
| `rssi` | ESP32 (real) | Intensidade do sinal WiFi (dBm) |
| `consumo_ma` | Estimativa | Consumo energetico (mA) |
| `latencia` | ESP32 (real) | Tempo de envio MQTT (ms) |
| `pacotes_enviados` | ESP32 (real) | Total de pacotes TX |
| `pacotes_confirmados` | ESP32 (real) | Total de pacotes confirmados |
| `dht_simulado` | ESP32 | 0 = dado real, 1 = fallback simulado |
| `failovers` | ESP32 (real) | Numero de trocas de servidor |

---

## Failover Automatico

O ESP32 implementa failover automatico entre GCP e AWS:

1. **Conexao primaria**: Google Cloud Platform (34.69.204.126)
2. **Apos 3 falhas consecutivas**: muda para AWS (100.31.105.129)
3. **A cada 60 segundos**: tenta reconectar ao servidor primario
4. **Retorno automatico**: quando GCP volta, ESP32 reconecta

### MQTT Bridge

As VMs possuem **MQTT Bridge** bidirecional, garantindo que dados enviados para uma VM sejam replicados para a outra em tempo real.

---

## Estrutura dos Arquivos

```
esp32-iot-saude/
├── esp32-iot-saude.ino    # Codigo principal do ESP32 (failover GCP/AWS)
├── mqtt_to_influx_aws.py  # Python Bridge (MQTT -> InfluxDB) para AWS
├── setup-aws.sh           # Script de instalacao da stack na EC2 AWS
├── sync_influx.py         # Sync de dados entre InfluxDBs (futuro)
├── pinagem.txt            # Referencia de pinagem ESP32 + DHT22
├── dht_scan/
│   └── dht_scan.ino       # Utilitario: scanner de GPIOs para DHT22
└── README.md
```

---

## Pinagem - ESP32 + DHT22

```
ESP32 3V3    ---> DHT22 pino 1 (VCC)
ESP32 GPIO4  ---> DHT22 pino 2 (DAT) + resistor 10k pull-up (opcional)
ESP32 GND    ---> DHT22 pino 4 (GND)
```

---

## Como Usar

### Pre-requisitos
- Arduino IDE com suporte ESP32
- Bibliotecas: `PubSubClient`, `DHT sensor library` (Adafruit)

### 1. Configurar WiFi
Editar `esp32-iot-saude.ino`, linhas 17-18:
```cpp
const char* ssid     = "SEU_WIFI";
const char* password = "SUA_SENHA";
```

### 2. Upload para ESP32
1. Conectar ESP32 via USB
2. Selecionar placa: **ESP32 Dev Module**
3. Upload (Ctrl+U)
4. Serial Monitor em 115200 baud

### 3. Verificar dados
```bash
# Na VM, ver dados MQTT em tempo real
mosquitto_sub -t "iot-saude-mestrado/#" -v

# Consultar InfluxDB
influx -database iot_medico -execute "SELECT * FROM metricas_iot ORDER BY time DESC LIMIT 5"
```

### 4. Grafana
- GCP: `http://34.69.204.126:3000`
- AWS: `http://100.31.105.129:3000`

---

## Proximos Passos

- [ ] Implementar protocolo LoRaWAN para comparativo
- [ ] Deploy do script de sincronizacao InfluxDB entre VMs
- [ ] Analise estatistica das metricas (Python/Pandas/Matplotlib)
- [ ] Exportar dados para CSV (Google Drive)
- [ ] Escrita do artigo com resultados comparativos

---

## Licenca

Projeto academico - Mestrado em Ciencia da Computacao, CIn/UFPE.
