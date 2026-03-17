/*
 * ESP32 MQTT Stress Test - Failover GCP/AWS
 * Mestrado CIn-UFPE - João Veloso
 *
 * ESP32 DevKit-C V4 + DHT22
 * Failover: tenta GCP primeiro, se cair muda para AWS
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// ============================================================
//  CONFIGURAÇÕES WiFi
// ============================================================
const char* ssid     = "NEO_VISITANTES";
const char* password = "neogenomicaparatodos";

// ============================================================
//  SERVIDORES MQTT - FAILOVER
// ============================================================
const char* servidores[]     = {"34.69.204.126", "100.31.105.129"};
const char* nomes_servidor[] = {"GCP", "AWS"};
const int   NUM_SERVIDORES   = 2;
const int   mqtt_port        = 1883;
const char* mqtt_topic       = "iot-saude-mestrado/esp32";

int servidor_atual           = 0;     // 0=GCP (primário), 1=AWS (backup)
int falhas_consecutivas      = 0;
const int MAX_FALHAS         = 3;     // após 3 falhas, muda de servidor
unsigned long ultimo_check_primario = 0;
const unsigned long INTERVALO_CHECK_PRIMARIO = 60000; // tenta voltar ao primário a cada 60s

// ============================================================
//  HARDWARE
// ============================================================
#define DHT_PIN   4
#define DHT_TYPE  DHT22

DHT dht(DHT_PIN, DHT_TYPE);
WiFiClient espClient;
PubSubClient mqtt_client(espClient);

// ============================================================
//  MÉTRICAS
// ============================================================
unsigned long pacotes_enviados       = 0;
unsigned long pacotes_confirmados    = 0;
unsigned long ultima_latencia        = 0;
unsigned long latencia_total         = 0;
unsigned long ultimo_update_serial   = 0;
unsigned long pacotes_ultimo_segundo = 0;
unsigned long failovers_total        = 0;

// Cache do DHT22
float  dht_temp   = 0.0;
float  dht_umid   = 0.0;
bool   dht_valido = false;
unsigned long ultima_leitura_dht = 0;
const unsigned long INTERVALO_DHT = 2000;

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println();
  Serial.println("==================================================");
  Serial.println("  ESP32 IoT Saude - FAILOVER GCP/AWS");
  Serial.println("  Mestrado CIn-UFPE - Joao Veloso");
  Serial.println("==================================================");
  Serial.printf("  Primario: %s (%s)\n", servidores[0], nomes_servidor[0]);
  Serial.printf("  Backup:   %s (%s)\n", servidores[1], nomes_servidor[1]);
  Serial.println("==================================================");

  dht.begin();
  Serial.println("[DHT22] Inicializado no GPIO" + String(DHT_PIN));

  conectarWiFi();

  mqtt_client.setServer(servidores[servidor_atual], mqtt_port);
  mqtt_client.setBufferSize(512);
}

// ============================================================
//  WIFI
// ============================================================
void conectarWiFi() {
  Serial.print("[WiFi] Conectando a ");
  Serial.print(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int tentativas = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    tentativas++;
    if (tentativas > 40) {
      Serial.println("\n[WiFi] FALHA! Reiniciando...");
      ESP.restart();
    }
  }

  Serial.println(" OK!");
  Serial.print("[WiFi] IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("[WiFi] RSSI: ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");
}

// ============================================================
//  MQTT COM FAILOVER
// ============================================================
void trocarServidor() {
  int anterior = servidor_atual;
  servidor_atual = (servidor_atual + 1) % NUM_SERVIDORES;
  falhas_consecutivas = 0;
  failovers_total++;

  Serial.printf("[FAILOVER] %s -> %s (failover #%lu)\n",
    nomes_servidor[anterior], nomes_servidor[servidor_atual], failovers_total);

  mqtt_client.disconnect();
  mqtt_client.setServer(servidores[servidor_atual], mqtt_port);
}

void tentarVoltarPrimario() {
  if (servidor_atual == 0) return;
  if (millis() - ultimo_check_primario < INTERVALO_CHECK_PRIMARIO) return;
  ultimo_check_primario = millis();

  Serial.printf("[FAILOVER] Tentando voltar ao primario (%s)...\n", nomes_servidor[0]);

  WiFiClient testClient;
  testClient.setTimeout(3);
  if (testClient.connect(servidores[0], mqtt_port)) {
    testClient.stop();
    Serial.printf("[FAILOVER] Primario disponivel! Reconectando...\n");
    servidor_atual = 0;
    falhas_consecutivas = 0;
    failovers_total++;
    mqtt_client.disconnect();
    mqtt_client.setServer(servidores[0], mqtt_port);
  } else {
    Serial.printf("[FAILOVER] Primario ainda indisponivel\n");
  }
}

void conectarMQTT() {
  int tentativas = 0;
  while (!mqtt_client.connected()) {
    String clientId = "ESP32_Real_" + String(nomes_servidor[servidor_atual]);
    Serial.printf("[MQTT] Conectando a %s (%s)...",
      servidores[servidor_atual], nomes_servidor[servidor_atual]);

    if (mqtt_client.connect(clientId.c_str())) {
      Serial.println(" OK!");
      falhas_consecutivas = 0;
      return;
    }

    falhas_consecutivas++;
    tentativas++;
    Serial.printf(" FALHA (rc=%d, falhas=%d/%d)\n",
      mqtt_client.state(), falhas_consecutivas, MAX_FALHAS);

    if (falhas_consecutivas >= MAX_FALHAS) {
      trocarServidor();
      tentativas = 0;
    } else {
      delay(1000);
    }

    if (tentativas > MAX_FALHAS * NUM_SERVIDORES) {
      Serial.println("[MQTT] Todos os servidores falharam! Aguardando 10s...");
      delay(10000);
      tentativas = 0;
    }
  }
}

// ============================================================
//  LEITURA DHT22
// ============================================================
void lerDHT22() {
  if (millis() - ultima_leitura_dht < INTERVALO_DHT) return;
  ultima_leitura_dht = millis();

  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (!isnan(t) && !isnan(h)) {
    dht_temp   = t;
    dht_umid   = h;
    dht_valido = true;
  } else {
    Serial.println("[DHT22] Erro na leitura!");
    dht_valido = false;
  }
}

// ============================================================
//  LOOP PRINCIPAL
// ============================================================
void loop() {
  if (WiFi.status() != WL_CONNECTED) conectarWiFi();

  tentarVoltarPrimario();

  if (!mqtt_client.connected()) conectarMQTT();
  mqtt_client.loop();

  lerDHT22();

  float temp = dht_valido ? dht_temp : (36.5 + (random(100) / 100.0));
  float umid = dht_valido ? dht_umid : (60.0 + random(20) - 10);
  int   fc   = 70 + random(20);
  int   spo2 = 95 + random(5);
  int   rssi = WiFi.RSSI();
  float consumo = 160 + random(40);

  pacotes_enviados++;

  String payload = "metricas_iot,protocolo=WiFi,dispositivo=ESP32_Real,localizacao=UTI-01,cloud=";
  payload += nomes_servidor[servidor_atual];
  payload += " temperatura=" + String(temp, 1);
  payload += ",umidade=" + String(umid, 1);
  payload += ",freq_cardiaca=" + String(fc);
  payload += ",saturacao_o2=" + String(spo2);
  payload += ",rssi=" + String(rssi);
  payload += ",consumo_ma=" + String(consumo, 1);
  payload += ",latencia=" + String(ultima_latencia);
  payload += ",pacotes_enviados=" + String(pacotes_enviados);
  payload += ",pacotes_confirmados=" + String(pacotes_confirmados);
  payload += ",dht_simulado=" + String(dht_valido ? 0 : 1);
  payload += ",failovers=" + String(failovers_total);

  unsigned long t1 = millis();

  if (mqtt_client.publish(mqtt_topic, payload.c_str())) {
    ultima_latencia = millis() - t1;
    latencia_total += ultima_latencia;
    pacotes_confirmados++;
    pacotes_ultimo_segundo++;
  }

  // Stats a cada 1 segundo
  if (millis() - ultimo_update_serial >= 1000) {
    float pdr = (pacotes_enviados > 0) ? (pacotes_confirmados * 100.0 / pacotes_enviados) : 0;
    float lat_media = (pacotes_confirmados > 0) ? (latencia_total / (float)pacotes_confirmados) : 0;
    unsigned long pps = pacotes_ultimo_segundo;

    Serial.printf("[%s] TX:%lu OK:%lu PDR:%.1f%% PPS:%lu Lat:%.1fms RSSI:%d DHT:%s T:%.1f H:%.1f FO:%lu\n",
      nomes_servidor[servidor_atual],
      pacotes_enviados, pacotes_confirmados, pdr, pps, lat_media, rssi,
      dht_valido ? "OK" : "SIM", temp, umid, failovers_total);

    ultimo_update_serial = millis();
    pacotes_ultimo_segundo = 0;
  }

  delay(10);
}
