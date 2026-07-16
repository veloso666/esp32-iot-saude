/* ============================================================
 *  No LoRaWAN - IoT Saude (mestrado)  [ENVIO CONTINUO + ENERGIA REAL]
 *  ESP32 + modulo Radioenge LoRaWAN (RD49C) + INA219
 *
 *  Fluxo: confere JOIN -> le sensor -> monta 9 bytes -> AT+SENDB
 *         mede a corrente do modulo com o INA219 (contagem de Coulomb)
 *         e envia a carga do ciclo anterior no proprio payload.
 *  Rede : ChirpStack (GCP 35.215.213.80), AU915 sub-banda 2, OTAA
 *
 *  ---- Ligacoes ----
 *  Modulo LoRaWAN (dados, como ja estava):
 *    ESP32 GPIO16 (RX2) <- TX do modulo
 *    ESP32 GPIO17 (TX2) -> RX do modulo
 *    GND comum
 *  INA219 (I2C) no ESP32:
 *    INA219 VCC -> 3V3 do ESP32
 *    INA219 GND -> GND
 *    INA219 SDA -> GPIO21
 *    INA219 SCL -> GPIO22
 *  INA219 medindo o modulo (em serie na alimentacao dele):
 *    3V3 do ESP32 -> INA219 Vin+
 *    INA219 Vin-  -> VIN do modulo LoRaWAN
 *    (assim toda a corrente do modulo passa pelo shunt do INA219)
 *
 *  Requer a lib "Adafruit INA219" (Gerenciador de Bibliotecas do Arduino).
 *
 *  Contrato de payload (9 bytes, big-endian):
 *    [0]   seq          uint8
 *    [1-2] temperatura  int16  (x100)
 *    [3]   umidade      uint8  (%)
 *    [4]   bpm          uint8
 *    [5]   spo2         uint8  (%)
 *    [6]   redundancia  uint8  (1 sem / 2 com)  <- FATOR do DoE
 *    [7-8] energia      uint16 (uAh do ciclo ANTERIOR; 0.001 mAh/unidade)
 * ============================================================ */

#include <Wire.h>
#include <Adafruit_INA219.h>

#define RXD2 16
#define TXD2 17
#define LORA Serial2
#define SDA_PIN 21
#define SCL_PIN 22

// ---- Parametros do experimento ----
#define REDUNDANCIA   2        // 1 (sem) ou 2 (com) - fator B do DoE
#define FPORT         2        // porta de aplicacao do uplink
#define INTERVALO_MS  1000UL   // alvo: 1s entre envios (envio continuo, sem limite)
#define RETRY_BUSY_MS 800UL    // reenvia rapido se o modulo estiver ocupado

Adafruit_INA219 ina219;
bool     temINA = false;

uint8_t  seq = 0;
uint16_t okCount = 0;                 // pacotes efetivamente enviados
uint16_t energiaCicloAnterior_uAh = 0;// carga medida do ultimo envio (uAh)

// ---- Energia (contagem de Coulomb) ----
double   mAh_total = 0.0;             // carga acumulada total (mAh)
uint32_t lastEnergyMs = 0;
double   ultCorrente_mA = 0.0;
double   ultTensao_V = 0.0;

void amostraEnergia() {
  if (!temINA) return;
  uint32_t agora = millis();
  double i_mA = ina219.getCurrent_mA();
  if (i_mA < 0) i_mA = 0;                        // descarta ruido negativo
  if (lastEnergyMs != 0) {
    double dt_h = (agora - lastEnergyMs) / 3600000.0;  // ms -> h
    mAh_total += i_mA * dt_h;
  }
  lastEnergyMs = agora;
  ultCorrente_mA = i_mA;
  ultTensao_V = ina219.getBusVoltage_V();
}

// delay que continua amostrando a energia enquanto espera
void esperaAmostrando(uint32_t ms) {
  uint32_t t0 = millis();
  while (millis() - t0 < ms) { amostraEnergia(); delay(5); }
}

// Envia um comando AT, amostrando energia enquanto espera a resposta.
String at(const String& cmd, uint32_t timeout = 2000) {
  while (LORA.available()) LORA.read();
  LORA.print(cmd); LORA.print("\r\n");
  Serial.print(">> "); Serial.println(cmd);
  String resp; uint32_t t0 = millis();
  while (millis() - t0 < timeout) {
    while (LORA.available()) resp += (char)LORA.read();
    amostraEnergia();
    if (resp.indexOf("OK") >= 0 || resp.indexOf("ERROR") >= 0) break;
  }
  resp.trim();
  if (resp.length()) { Serial.print("<< "); Serial.println(resp); }
  return resp;
}

void garantirJoin() {
  String s = at("AT+NJS=?", 2000);
  if (s.indexOf("1") >= 0) { Serial.println("[JOIN] modulo ja esta na rede."); return; }
  Serial.println("[JOIN] modulo fora da rede, tentando entrar...");
  for (int tentativa = 1; ; tentativa++) {
    Serial.printf("[JOIN] tentativa %d...\n", tentativa);
    at("AT+JOIN", 8000);
    esperaAmostrando(6000);
    s = at("AT+NJS=?", 2000);
    if (s.indexOf("1") >= 0) { Serial.println("[JOIN] OK - na rede!"); return; }
    Serial.println("[JOIN] ainda nao... nova tentativa em 10s");
    esperaAmostrando(10000);
  }
}

// TODO: troque por leitura do sensor real (MAX30102, sensor de temp, etc.).
void lerSensor(float& tempC, uint8_t& umid, uint8_t& bpm, uint8_t& spo2) {
  tempC = 36.5 + (random(-80, 80) / 100.0);
  umid  = random(40, 65);
  bpm   = random(60, 110);
  spo2  = random(94, 100);
}

// Retorna true se o modulo confirmou o envio (AT_TX_OK).
bool enviarUplink() {
  float tempC; uint8_t umid, bpm, spo2;
  lerSensor(tempC, umid, bpm, spo2);

  int16_t t100 = (int16_t)lround(tempC * 100.0);
  uint8_t buf[9];
  buf[0] = seq++;
  buf[1] = (uint8_t)((t100 >> 8) & 0xFF);
  buf[2] = (uint8_t)(t100 & 0xFF);
  buf[3] = umid;
  buf[4] = bpm;
  buf[5] = spo2;
  buf[6] = REDUNDANCIA;
  buf[7] = (uint8_t)((energiaCicloAnterior_uAh >> 8) & 0xFF);
  buf[8] = (uint8_t)(energiaCicloAnterior_uAh & 0xFF);

  char hex[19];
  for (int i = 0; i < 9; i++) sprintf(hex + i * 2, "%02X", buf[i]);
  hex[18] = '\0';

  double mAh_antes = mAh_total;
  String r = at(String("AT+SENDB=") + FPORT + ":" + hex, 6000);
  amostraEnergia();
  double energiaCiclo_mAh = mAh_total - mAh_antes;                 // carga deste envio
  double v = energiaCiclo_mAh * 1000.0;                           // -> uAh
  if (v < 0) v = 0; if (v > 65535) v = 65535;
  energiaCicloAnterior_uAh = (uint16_t)lround(v);                 // vai no proximo payload

  if (r.indexOf("TX_OK") >= 0) {
    okCount++;
    Serial.printf("[TX %u] OK  temp=%.2f bpm=%u spo2=%u red=%d | I=%.1fmA V=%.2fV | ciclo=%.4fmAh total=%.4fmAh\n",
                  okCount, tempC, bpm, spo2, REDUNDANCIA,
                  ultCorrente_mA, ultTensao_V, energiaCiclo_mAh, mAh_total);
    return true;
  }
  if (r.indexOf("BUSY") >= 0) Serial.println("[TX] modulo ocupado (RX1/RX2) - reenviando...");
  else                        Serial.println("[TX] sem confirmacao - reenviando...");
  return false;
}

void setup() {
  Serial.begin(115200);
  LORA.begin(9600, SERIAL_8N1, RXD2, TXD2);
  Wire.begin(SDA_PIN, SCL_PIN);
  delay(500);
  Serial.println("\n=== No LoRaWAN IoT Saude (rajada + energia INA219) ===");

  if (ina219.begin()) {
    temINA = true;
    // ina219.setCalibration_16V_400mA();  // opcional: melhor resolucao p/ correntes baixas
    Serial.println("[INA219] detectado - medindo energia real.");
  } else {
    Serial.println("[INA219] NAO detectado! Verifique SDA=21/SCL=22/VCC/GND. Segue sem energia medida.");
  }

  at("AT+DEUI=?");
  garantirJoin();
  Serial.println("[LOOP] envio continuo (alvo 1s, reenvia se BUSY, sem limite)...");
}

void loop() {
  bool ok = enviarUplink();
  esperaAmostrando(ok ? INTERVALO_MS : RETRY_BUSY_MS);
}
