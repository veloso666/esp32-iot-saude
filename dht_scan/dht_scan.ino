/*
 * DHT22 Pin Scanner - Diagnóstico
 * Testa múltiplos GPIOs para encontrar o DHT22
 */

#include <DHT.h>

const int pinos[] = {2, 4, 5, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27};
const int total = sizeof(pinos) / sizeof(pinos[0]);

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("=== DHT22 PIN SCANNER ===");
  Serial.println("Testando todos os GPIOs...\n");
}

void loop() {
  for (int i = 0; i < total; i++) {
    DHT dht(pinos[i], DHT22);
    dht.begin();
    delay(2500);

    float t = dht.readTemperature();
    float h = dht.readHumidity();

    if (!isnan(t) && !isnan(h)) {
      Serial.printf(">>> GPIO %d: ENCONTRADO! Temp=%.1f Umid=%.1f <<<\n", pinos[i], t, h);
    } else {
      Serial.printf("    GPIO %d: sem resposta\n", pinos[i]);
    }
  }

  Serial.println("\n--- Scan completo. Reiniciando em 5s... ---\n");
  delay(5000);
}
