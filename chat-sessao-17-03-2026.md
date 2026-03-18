# Sessao de Trabalho - IoT Saude Mestrado
**Data:** 17 de marco de 2026
**Mestrado CIn/UFPE - Joao Lucas Veloso**

---

## 1. Acesso a VM no Google Cloud

O primeiro passo foi recuperar o acesso a VM no Google Cloud Platform (IP: 34.69.204.126, zona: us-central1-a). A VM ja estava rodando com todos os servicos ativos:

- **Mosquitto** (MQTT Broker) - porta 1883, rodando desde 03/02
- **InfluxDB** (Time Series DB) - porta 8086, banco `iot_medico`
- **Grafana** (Dashboard) - porta 3000
- **Python Bridge** (`mqtt_to_influx.py`) - MQTT para InfluxDB

Configuracao do Mosquitto:
```
listener 1883 0.0.0.0
allow_anonymous true
```

O bridge Python aceita dois formatos de payload: InfluxDB Line Protocol e JSON.

---

## 2. Adaptacao do Codigo Wokwi para Hardware Real

O codigo original do Wokwi foi adaptado para o ESP32 fisico com as seguintes mudancas:

- **WiFi**: credenciais reais (NEO_VISITANTES) em vez de Wokwi-GUEST
- **DHT22 real**: leitura com cache de 2s (sensor e lento), com fallback para dados simulados
- **GPIO4**: trocado de GPIO15 (strapping pin com pull-down interno que conflita com DHT22)
- **Sem display OLED nem LEDs**: simplificado, feedback apenas via Serial Monitor
- **Bibliotecas**: WiFi.h, PubSubClient, DHT.h

### Problema: GPIO15
O GPIO15 e um "strapping pin" do ESP32 que tem pull-down interno, conflitando com o DHT22 que precisa de pull-up. No Wokwi funciona porque e simulado, mas no hardware real causa erro de leitura. Solucao: mudar para GPIO4.

### Diagnostico: DHT22 Pin Scanner
Criado utilitario `dht_scan.ino` que testa automaticamente todos os GPIOs para encontrar onde o DHT22 esta conectado. Resultado:
```
>>> GPIO 4: ENCONTRADO! Temp=22.4 Umid=79.3 <<<
```

---

## 3. Montagem Fisica

### Componentes
- ESP32 DevKit-C V4
- DHT22 (sensor de temperatura/umidade)
- Protoboard
- 3 jumpers macho-femea

### Pinagem Final
```
ESP32 3V3    ---> DHT22 pino 1 (VCC)
ESP32 GPIO4  ---> DHT22 pino 2 (DAT)
ESP32 GND    ---> DHT22 pino 4 (GND)
```

DHT22 na fileira J da protoboard (colunas 1-4), jumpers na fileira G (mesmas colunas). Sem resistor pull-up externo (nao necessario neste modulo).

---

## 4. Driver USB e Upload

O ESP32 usa chip **CP2102** para comunicacao USB. O Windows nao reconheceu automaticamente - foi necessario instalar o driver da Silicon Labs (CP210x VCP Drivers).

Upload via Arduino IDE:
- Placa: ESP32 Dev Module
- Bibliotecas: PubSubClient (Nick O'Leary), DHT sensor library (Adafruit)
- Upload speed: 921600
- Resultado: 913.251 bytes (69% do armazenamento)

---

## 5. Resultados do Primeiro Teste

```
[WiFi] IP: 192.168.70.111
[WiFi] RSSI: -71 dBm
[MQTT] Conectando a 34.69.204.126... OK!
[STATS] TX:33 OK:33 PDR:100.0% PPS:32 Lat:19.8ms RSSI:-71 DHT:OK T:21.8 H:63.6
```

Pipeline completa funcionando:
- **ESP32** -> WiFi -> **Mosquitto** (GCP) -> **Python Bridge** -> **InfluxDB** -> **Grafana**
- PDR: 100%
- PPS: ~28-35 pacotes/segundo
- Latencia: ~20-40ms
- Temperatura real: 21.8C, Umidade: 63.6%

Dados confirmados no InfluxDB:
```
influx -database iot_medico -execute "SELECT * FROM metricas_iot ORDER BY time DESC LIMIT 5"
```

---

## 6. Criacao da VM na AWS (Failover)

### Objetivo
Implementar failover automatico: se a conexao com a GCP cair, o ESP32 muda para a AWS.

### EC2 Criada
- **Instancia**: t3.micro (free tier)
- **AMI**: Ubuntu 22.04 (ami-04680790a315cd58d)
- **IP**: 100.31.105.129
- **Regiao**: us-east-1
- **Security Group**: portas 22, 1883, 8086, 3000

### Stack Instalada na AWS
Mesma stack da GCP, via script `setup-aws.sh`:
1. **Mosquitto** - broker MQTT, porta 1883, allow_anonymous true
2. **InfluxDB** - banco `iot_medico`, porta 8086
3. **Grafana** - dashboard, porta 3000 (admin/admin)
4. **Python Bridge** - `mqtt_to_influx.py` como servico systemd (`mqtt-bridge.service`)

Nota: a versao do paho-mqtt na AWS e 2.x, que exige `mqtt.CallbackAPIVersion.VERSION2` no construtor do Client.

---

## 7. Failover no ESP32

### Logica Implementada
- Array de servidores: `{"34.69.204.126", "100.31.105.129"}`
- Apos **3 falhas consecutivas**, troca de servidor
- A cada **60 segundos**, tenta voltar ao primario (GCP)
- Tag `cloud=GCP` ou `cloud=AWS` no payload para rastreabilidade
- Contador de failovers no payload

### Teste de Failover
```
[GCP] TX:835 OK:834 PDR:99.9% PPS:21 Lat:38.7ms RSSI:-62 DHT:OK T:21.9 H:70.0 FO:0
[MQTT] Conectando a 34.69.204.126 (GCP)... FALHA (rc=-2, falhas=1/3)
[MQTT] Conectando a 34.69.204.126 (GCP)... FALHA (rc=-2, falhas=2/3)
[MQTT] Conectando a 34.69.204.126 (GCP)... FALHA (rc=-2, falhas=3/3)
[FAILOVER] GCP -> AWS (failover #1)
[MQTT] Conectando a 100.31.105.129 (AWS)... OK!
[AWS] TX:836 OK:835 PDR:99.9% PPS:1 Lat:38.7ms RSSI:-64 DHT:OK T:21.9 H:70.0 FO:1
```

Failover em ~3 segundos, sem perda de dados.

---

## 8. MQTT Bridge (Replicacao entre VMs)

### Objetivo
Garantir que ambas as VMs tenham os mesmos dados, independente de para qual o ESP32 esta enviando.

### Configuracao
Cada Mosquitto recebeu um arquivo de bridge:

**GCP** (`/etc/mosquitto/conf.d/bridge-aws.conf`):
```
connection bridge-to-aws
address 100.31.105.129:1883
topic iot-saude-mestrado/# both 0
topic hospital/# both 0
try_private false
start_type automatic
restart_timeout 5
```

**AWS** (`/etc/mosquitto/conf.d/bridge-gcp.conf`):
```
connection bridge-to-gcp
address 34.69.204.126:1883
topic iot-saude-mestrado/# both 0
topic hospital/# both 0
try_private false
start_type automatic
restart_timeout 5
```

### Resultado
Dados com `cloud=GCP` aparecendo na AWS, confirmando replicacao em tempo real:
```
iot-saude-mestrado/esp32 metricas_iot,...,cloud=GCP temperatura=21.7,...
```

InfluxDB da AWS gravando dados originados na GCP com sucesso.

---

## 9. Sync InfluxDB (Ponto Futuro)

Script `sync_influx.py` criado para sincronizar dados faltantes entre os InfluxDBs (para cobrir periodos de downtime). Deploy e configuracao de cron ficaram como ponto futuro.

---

## 10. GitHub

Repositorio criado: **https://github.com/veloso666/esp32-iot-saude**

Arquivos enviados:
- `README.md` - Documentacao completa
- `esp32-iot-saude.ino` - Codigo principal ESP32 com failover
- `mqtt_to_influx_aws.py` - Python Bridge para AWS
- `setup-aws.sh` - Script de instalacao da stack AWS
- `sync_influx.py` - Sync entre InfluxDBs (futuro)
- `pinagem.txt` - Referencia de pinagem
- `dht_scan/dht_scan.ino` - Scanner de GPIOs

---

## Resumo de Infraestrutura

| Recurso | GCP | AWS |
|---|---|---|
| **IP** | 34.69.204.126 | 100.31.105.129 |
| **Mosquitto** | Porta 1883 | Porta 1883 |
| **InfluxDB** | Porta 8086 | Porta 8086 |
| **Grafana** | Porta 3000 | Porta 3000 |
| **Bridge** | Replica para AWS | Replica para GCP |
| **SSH** | Console GCP | `ssh -i ~/.ssh/iot-saude-aws4.pem ubuntu@100.31.105.129` |

## Proximos Passos

- [ ] Implementar protocolo LoRaWAN (solicitar modulo ao orientador)
- [ ] Deploy do sync_influx.py com cron
- [ ] Criar dashboards no Grafana
- [ ] Analise estatistica com Python/Pandas/Matplotlib
- [ ] Exportar dados para CSV
- [ ] Escrita do artigo comparativo
