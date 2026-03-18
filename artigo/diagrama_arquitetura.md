# Diagrama de Arquitetura - IoT Saude Mestrado

## Diagrama completo (para artigo)

Usar este Mermaid para gerar a imagem:

```mermaid
flowchart TB
    subgraph sensores [Camada de Sensores]
        ESP32["ESP32 DevKit-C V4"]
        DHT22["DHT22\nTemp/Umidade"]
        SIM["Simulado\nFC | SpO2"]
        ESP32 --- DHT22
        ESP32 --- SIM
        METRICAS["Metricas: Latencia | PDR | RSSI\nJitter | Disponibilidade | Consumo"]
    end

    subgraph protocolos [Protocolos]
        WIFI["WiFi\n802.11 b/g/n"]
        LORAWAN["LoRaWAN\n(Futuro)"]
    end

    subgraph gcp [Google Cloud Platform - 136.115.185.214]
        MQTT_GCP["Mosquitto\nMQTT Broker\nPorta 1883"]
        BRIDGE_GCP["Python Bridge\nMQTT to InfluxDB"]
        INFLUX_GCP["InfluxDB\nTime Series DB\nPorta 8086"]
        GRAFANA_GCP["Grafana\nDashboard\nPorta 3000"]
        INJETOR["Injetor de Falhas\ninjetor_falhas.py"]

        MQTT_GCP --> BRIDGE_GCP
        BRIDGE_GCP --> INFLUX_GCP
        INFLUX_GCP --> GRAFANA_GCP
        INJETOR -.->|"stop/start\nMosquitto"| MQTT_GCP
    end

    subgraph aws [Amazon Web Services - 23.21.181.24]
        MQTT_AWS["Mosquitto\nMQTT Broker\nPorta 1883"]
        BRIDGE_AWS["Python Bridge\nMQTT to InfluxDB"]
        INFLUX_AWS["InfluxDB\nTime Series DB\nPorta 8086"]
        GRAFANA_AWS["Grafana\nDashboard\nPorta 3000"]

        MQTT_AWS --> BRIDGE_AWS
        BRIDGE_AWS --> INFLUX_AWS
        INFLUX_AWS --> GRAFANA_AWS
    end

    subgraph analise [Analise e Resultados]
        MONITOR["Monitor de Eventos\nmonitor_eventos.py"]
        EXPORT["Export CSV\nGoogle Drive"]
        PYTHON["Python\nPandas/Matplotlib"]
        DISS["Dissertacao\nAnalise Estatistica"]
    end

    ESP32 -->|"MQTT\n(primario)"| WIFI
    WIFI -->|"Failover"| MQTT_GCP
    WIFI -.->|"Backup"| MQTT_AWS

    MQTT_GCP <-->|"MQTT Bridge\nReplicacao"| MQTT_AWS

    INFLUX_GCP --> EXPORT
    INFLUX_AWS --> EXPORT
    EXPORT --> PYTHON
    PYTHON --> DISS
    MONITOR -.->|"TCP check"| MQTT_GCP
    MONITOR -.->|"TCP check"| MQTT_AWS
```

## Diagrama simplificado (fluxo de dados)

```mermaid
flowchart LR
    ESP32["ESP32\n+DHT22"] -->|"WiFi/MQTT"| GCP["GCP\nMosquitto"]
    ESP32 -.->|"failover"| AWS["AWS\nMosquitto"]
    GCP <-->|"MQTT Bridge"| AWS
    GCP --> DB1["InfluxDB"] --> G1["Grafana"]
    AWS --> DB2["InfluxDB"] --> G2["Grafana"]
    INJETOR["Injetor\nde Falhas"] -.->|"stop/start"| GCP
    MONITOR["Monitor\nde Eventos"] -.->|"TCP check"| GCP
    MONITOR -.->|"TCP check"| AWS
```

## Diagrama de injecao de falhas

```mermaid
sequenceDiagram
    participant INJ as Injetor de Falhas
    participant MQTT as Mosquitto (GCP)
    participant ESP as ESP32
    participant AWS as Mosquitto (AWS)

    Note over MQTT: Sistema Operando
    ESP->>MQTT: publish (cloud=GCP)

    INJ->>MQTT: systemctl stop mosquitto
    Note over MQTT: FALHA INJETADA

    ESP->>MQTT: publish FALHA (1/3)
    ESP->>MQTT: publish FALHA (2/3)
    ESP->>MQTT: publish FALHA (3/3)
    Note over ESP: FAILOVER detectado

    ESP->>AWS: connect + publish (cloud=AWS)
    Note over AWS: ESP32 no backup

    INJ->>MQTT: systemctl start mosquitto
    Note over MQTT: REPARO

    ESP->>MQTT: check primario (TCP)
    Note over ESP: Primario disponivel!
    ESP->>MQTT: reconnect + publish (cloud=GCP)
```
