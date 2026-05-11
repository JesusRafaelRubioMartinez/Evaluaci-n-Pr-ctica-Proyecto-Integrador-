#include <Wire.h>

void setup() {
  Wire.begin();
  Serial.begin(9600);
  Serial.println("Escaneando bus I2C...");
  Serial.println("Rango: 0x08 - 0x77\n");

  int dispositivos = 0;
  for (byte addr = 8; addr < 120; addr++) {
    Wire.beginTransmission(addr);
    byte error = Wire.endTransmission();

    if (error == 0) {
      dispositivos++;
      Serial.print("Dispositivo en: 0x");
      if (addr < 16) Serial.print("0");
      Serial.println(addr, HEX);
    }
  }

  Serial.println();
  Serial.print("Total de dispositivos: ");
  Serial.println(dispositivos);
  if (dispositivos == 0) {
    Serial.println("Ninguno encontrado. Verifica conexiones y pull-ups.");
  }
}

void loop() {}