#include <Wire.h>
#include <Adafruit_BMP085.h>
#include <Adafruit_SSD1306.h>

#define OLED_W 128
#define OLED_H 64
#define OLED_ADDR 0x3C

Adafruit_BMP085 bmp;
Adafruit_SSD1306 display(OLED_W, OLED_H, &Wire, -1);

void setup() {
  Serial.begin(9600);

  // 1. Iniciar la pantalla OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("ERROR: OLED no encontrada");
    while (true);
  }

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(15, 28);
  display.println("Iniciando BMP180...");
  display.display();
  delay(1000);

  // 2. Iniciar el sensor BMP180
  if (!bmp.begin()) {
    Serial.println("ERROR: BMP180 no encontrado");
    display.clearDisplay();
    display.setCursor(5, 28);
    display.println("ERROR: BMP180");
    display.display();
    while (true);
  }

  Serial.println("Componentes listos.");
}

void loop() {
  // Leer los datos del sensor
  float temp = bmp.readTemperature(); 
  float presion = bmp.readPressure() / 100.0; // Convertir de Pa a hPa
  float altitud = bmp.readAltitude(); 

  // Limpiar la pantalla para el nuevo cuadro
  display.clearDisplay();

  // Imprimir el Título
  display.setTextSize(1);
  display.setCursor(30, 0);
  display.println("-- BMP180 --");

  // Imprimir la Temperatura en grande
  display.setTextSize(2);
  display.setCursor(0, 15);
  display.print(temp, 1);
  display.println(" C");

  // Imprimir Presión y Altitud en pequeño
  display.setTextSize(1);
  display.setCursor(0, 38);
  display.print("P: ");
  display.print(presion, 1);
  display.println(" hPa");

  display.setCursor(0, 50);
  display.print("Alt: ");
  display.print(altitud, 0);
  display.println(" m");

  // Enviar toda la información a la pantalla
  display.display(); 

  // También lo enviamos al Monitor Serial para tener un registro
  Serial.print("Temp: ");
  Serial.print(temp, 1);
  Serial.print(" C \t Presion: ");
  Serial.print(presion, 1);
  Serial.println(" hPa");

  // Esperar un segundo antes de la siguiente lectura
  delay(1000);
}