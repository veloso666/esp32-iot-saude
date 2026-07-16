/* ============================================================
 *  No LoRaWAN - IoT Saude (mestrado)  [ENVIO CONTINUO]
 *  ESP32 + modulo Radioenge LoRaWAN (RD49C) via UART/AT
 *
 *  Fluxo: confere JOIN -> le sensor -> monta 7 bytes -> AT+SENDB
 *         repete continuamente (sem limite de pacotes)
 *  Rede : ChirpStack (GCP 35.215.213.80), AU915 sub-banda 2, OTAA
 *
 *  IMPORTANTE: este sketch NAO regrava APPEUI/APPKEY/CHMASK.
 *  Essas credenciais ja estao gravadas no modulo (persistem em flash).
 *  Regravar o AppKey sem power-cycle causa "Invalid MIC" no JOIN.
 *
 *  Ligacao:
 *    ESP32 GPIO16 (RX2) <- TX do modulo
 *    ESP32 GPIO17 (TX2) -> RX do modulo
 *    GND-GND ; VIN do modulo em 3V3
 *
 *  Contrato de payload (7 bytes, big-endian) - bate com o codec do ChirpStack:
 *    [0]   seq          uint8
 *    [1-2] temperatura  int16  (valor x100; ex.: 3660 = 36.60 C)
 *    [3]   umidade      uint8  (%)
 *    [4]   bpm          uint8
 *    [5]   spo2         uint8  (%)
 *    [6]   redundancia  uint8  (1 = sem, 2 = com)  <- FATOR do DoE
 * ============================================================ */

#define RXD2 16
#define TXD2 17
#define LORA Serial2

// ---- Parametros do experimento ----
#define REDUNDANCIA   2        // 1 (sem) ou 2 (com) - fator B do DoE
#define FPORT         2        // porta de aplicacao do uplink
#define INTERVALO_MS  1000UL   // alvo: 1s entre envios (envio continuo, sem limite)
#define RETRY_BUSY_MS 800UL    // reenvia rapido se o modulo estiver ocupado

uint8_t  seq = 0;
uint16_t okCount = 0;          // pacotes efetivamente enviados

// Envia um comando AT e coleta a resposta por ate 'timeout' ms.
String at(const String& cmd, uint32_t timeout = 2000) {
  while (LORA.available()) LORA.read();
  LORA.print(cmd); LORA.print("\r\n");
  Serial.print(">> "); Serial.println(cmd);
  String resp; uint32_t t0 = millis();
  while (millis() - t0 < timeout) {
    while (LORA.available()) resp += (char)LORA.read();
    if (resp.indexOf("OK") >= 0 || resp.indexOf("ERROR") >= 0) break;
  }
  resp.trim();
  if (resp.length()) { Serial.print("<< "); Serial.println(resp); }
  return resp;
}

// Garante que o modulo esta na rede. NAO regrava chaves.
void garantirJoin() {
  String s = at("AT+NJS=?", 2000);
  if (s.indexOf("1") >= 0) { Serial.println("[JOIN] modulo ja esta na rede."); return; }
  Serial.println("[JOIN] modulo fora da rede, tentando entrar...");
  for (int tentativa = 1; ; tentativa++) {
    Serial.printf("[JOIN] tentativa %d...\n", tentativa);
    at("AT+JOIN", 8000);
    delay(6000);
    s = at("AT+NJS=?", 2000);
    if (s.indexOf("1") >= 0) { Serial.println("[JOIN] OK - na rede!"); return; }
    Serial.println("[JOIN] ainda nao... nova tentativa em 10s");
    delay(10000);
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
  uint8_t buf[7];
  buf[0] = seq++;
  buf[1] = (uint8_t)((t100 >> 8) & 0xFF);
  buf[2] = (uint8_t)(t100 & 0xFF);
  buf[3] = umid;
  buf[4] = bpm;
  buf[5] = spo2;
  buf[6] = REDUNDANCIA;

  char hex[15];
  for (int i = 0; i < 7; i++) sprintf(hex + i * 2, "%02X", buf[i]);
  hex[14] = '\0';

  String r = at(String("AT+SENDB=") + FPORT + ":" + hex, 6000);
  if (r.indexOf("TX_OK") >= 0) {
    okCount++;
    Serial.printf("[TX %u] OK  temp=%.2f umid=%u bpm=%u spo2=%u red=%d\n",
                  okCount, tempC, umid, bpm, spo2, REDUNDANCIA);
    return true;
  }
  if (r.indexOf("BUSY") >= 0) Serial.println("[TX] modulo ocupado (RX1/RX2) - reenviando...");
  else                        Serial.println("[TX] sem confirmacao - reenviando...");
  return false;
}

void setup() {
  Serial.begin(115200);
  LORA.begin(9600, SERIAL_8N1, RXD2, TXD2);
  delay(500);
  Serial.println("\n=== No LoRaWAN IoT Saude (envio continuo) ===");
  at("AT+DEUI=?");
  garantirJoin();
  Serial.println("[LOOP] envio continuo (alvo 1s, reenvia se BUSY, sem limite)...");
}

void loop() {
  bool ok = enviarUplink();
  delay(ok ? INTERVALO_MS : RETRY_BUSY_MS);
}
