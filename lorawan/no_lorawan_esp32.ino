/* ============================================================
 *  No LoRaWAN - IoT Saude (mestrado)
 *  ESP32 + modulo Radioenge LoRaWAN (RD49C) via UART/AT
 *
 *  Fluxo: le sensor -> monta 7 bytes (contrato) -> AT+SENDB
 *  Rede : ChirpStack (GCP 35.215.213.80), AU915 sub-banda 2, OTAA
 *
 *  Ligacao (mesma que funcionou na deteccao):
 *    ESP32 GPIO16 (RX2) <- TX do modulo
 *    ESP32 GPIO17 (TX2) -> RX do modulo
 *    GND-GND ; VIN do modulo em 3V3
 *
 *  Contrato de payload (7 bytes, big-endian) - bate com o codec do ChirpStack:
 *    [0]   seq          uint8  (0-255, wrap)
 *    [1-2] temperatura  int16  (valor x100; ex.: 3660 = 36.60 C)
 *    [3]   umidade      uint8  (%)
 *    [4]   bpm          uint8  (freq. cardiaca)
 *    [5]   spo2         uint8  (saturacao O2 %)
 *    [6]   redundancia  uint8  (1 = sem, 2 = com)  <- FATOR do DoE
 * ============================================================ */

#define RXD2 16
#define TXD2 17
#define LORA Serial2

// ---- Credenciais OTAA (iguais ao ChirpStack) ----
const char* APPEUI = "00:00:00:00:00:00:00:00";
const char* APPKEY = "03:ac:61:11:21:08:c8:c4:46:c1:39:35:63:26:dc:fc";
// DevEUI e de fabrica (0012F80000003BB8) - nao precisa setar.

// ---- Parametros do experimento ----
#define REDUNDANCIA   2        // 1 (sem) ou 2 (com) - fator B do DoE
#define FPORT         2        // porta de aplicacao do uplink
#define INTERVALO_MS  60000UL  // 60s entre envios (respeita duty cycle)

uint8_t seq = 0;

// Envia um comando AT e coleta a resposta por ate 'timeout' ms.
String at(const String& cmd, uint32_t timeout = 2000) {
  while (LORA.available()) LORA.read();      // limpa buffer
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

// Configura OTAA e tenta juntar a rede (bloqueante ate conseguir).
void joinNetwork() {
  at("AT+NJM=1");                              // OTAA
  at("AT+CLASS=A");
  at(String("AT+APPEUI=") + APPEUI);
  at(String("AT+APPKEY=") + APPKEY);
  at("AT+CHMASK=ff00:0000:0000:0000:0002:0000"); // AU915 sub-banda 2
  at("AT+ADR=1");

  for (int tentativa = 1; ; tentativa++) {
    Serial.printf("\n[JOIN] tentativa %d...\n", tentativa);
    at("AT+JOIN", 8000);
    delay(6000);
    String s = at("AT+NJS=?", 2000);
    if (s.indexOf("1") >= 0) { Serial.println("[JOIN] OK - na rede!"); return; }
    Serial.println("[JOIN] ainda nao... nova tentativa em 10s");
    delay(10000);
  }
}

// TODO: troque por leitura do sensor real (ex.: MAX30102 p/ bpm/spo2, sensor de temp).
void lerSensor(float& tempC, uint8_t& umid, uint8_t& bpm, uint8_t& spo2) {
  tempC = 36.5 + (random(-80, 80) / 100.0);   // 35.7 .. 37.3
  umid  = random(40, 65);
  bpm   = random(60, 110);
  spo2  = random(94, 100);
}

void enviarUplink() {
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

  Serial.printf("[SENSOR] temp=%.2f umid=%u bpm=%u spo2=%u red=%d\n",
                tempC, umid, bpm, spo2, REDUNDANCIA);
  String r = at(String("AT+SENDB=") + FPORT + ":" + hex, 6000);
  if (r.indexOf("TX_OK") >= 0) Serial.println("[TX] enviado OK");
  else Serial.println("[TX] sem confirmacao (pode ser duty cycle/janela)");
}

void setup() {
  Serial.begin(115200);
  LORA.begin(9600, SERIAL_8N1, RXD2, TXD2);
  delay(500);
  Serial.println("\n=== No LoRaWAN IoT Saude ===");
  at("AT+DEUI=?");            // mostra o DevEUI de fabrica
  joinNetwork();
}

void loop() {
  enviarUplink();
  delay(INTERVALO_MS);
}
