#include <Arduino.h>
#include <DHT.h>
#include <ESP32Servo.h>
#include <WiFi.h>
#include <ThingSpeak.h>
#include "secrets.h"

// ─── Pines ────────────────────────────────────────────────
#define DHT_PIN    19   // GPIO donde está conectado el DATA del DHT22
#define SERVO_PIN   4   // GPIO donde está conectado la señal del servo

// ─── Configuración DHT ────────────────────────────────────
#define DHT_TYPE DHT22
DHT dht(DHT_PIN, DHT_TYPE);

// ─── Configuración Servo ──────────────────────────────────
Servo servo;

// ─── Configuración WiFi / ThingSpeak ──────────────────────
char ssid[]  = SECRET_SSID; 
char pass[]  = SECRET_PASS; 
WiFiClient client;

unsigned long myChannelNumber  = SECRET_CH_ID;
const char*   myWriteAPIKey    = SECRET_WRITE_APIKEY;

// ─── Tiempos ──────────────────────────────────────────────
unsigned long lastDHT       = 0;
unsigned long lastServo     = 0;
unsigned long lastThingSpeak = 0;

const unsigned long INTERVALO_DHT        = 2000;   // ms entre lecturas del DHT22
const unsigned long INTERVALO_SERVO      = 15;     // ms entre cada paso del servo
const unsigned long INTERVALO_THINGSPEAK = 10000;  // ms entre envíos (mín. 15 s en cuenta gratuita)

// ─── Estado del barrido ───────────────────────────────────
int servoPos = 0;
int servoDir = 1;   // 1 = subiendo, -1 = bajando

// ─── Últimas lecturas válidas ─────────────────────────────
float temperatura = NAN;
float humedad     = NAN;

// ─── Helpers ──────────────────────────────────────────────
void conectarWiFi() {
    if (WiFi.status() == WL_CONNECTED) return;

    Serial.printf("\nConectando a %s", ssid);
    WiFi.begin(ssid, pass);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\nWiFi conectado — IP: %s\n", WiFi.localIP().toString().c_str());
}

// ─── Setup ────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    Serial.println("=== ESP32 | DHT22 + Servo SG90 + ThingSpeak ===");

    // DHT
    dht.begin();

    // Servo
    servo.attach(SERVO_PIN, 500, 2400);
    servo.write(0);
    Serial.println("Servo en 0° — iniciando barrido automático");

    // WiFi + ThingSpeak
    WiFi.mode(WIFI_STA);
    conectarWiFi();
    ThingSpeak.begin(client);
}

// ─── Loop ─────────────────────────────────────────────────
void loop() {
    unsigned long ahora = millis();

    // ── Mantener conexión WiFi ───────────────────────────────
    conectarWiFi();

    // ── Leer DHT22 cada 2 segundos ──────────────────────────
    if (ahora - lastDHT >= INTERVALO_DHT) {
        lastDHT = ahora;

        float h = dht.readHumidity();
        float t = dht.readTemperature();

        if (isnan(h) || isnan(t)) {
            Serial.println("[ERROR] No se pudo leer el DHT22. Revisa el cableado.");
        } else {
            temperatura = t;
            humedad     = h;
            Serial.printf("[DHT22] Temp: %.1f °C  |  Humedad: %.1f %%\n", temperatura, humedad);
        }
    }

    // ── Barrido automático del servo ─────────────────────────
    if (ahora - lastServo >= INTERVALO_SERVO) {
        lastServo = ahora;

        servoPos += servoDir;

        if (servoPos >= 180) {
            servoPos = 180;
            servoDir = -1;
        } else if (servoPos <= 0) {
            servoPos = 0;
            servoDir = 1;
        }

        servo.write(servoPos);
    }

    // ── Enviar a ThingSpeak cada 20 segundos ─────────────────
    if (ahora - lastThingSpeak >= INTERVALO_THINGSPEAK) {
        lastThingSpeak = ahora;

        if (!isnan(temperatura) && !isnan(humedad)) {
            ThingSpeak.setField(1, temperatura);
            ThingSpeak.setField(2, humedad);

            int httpCode = ThingSpeak.writeFields(myChannelNumber, myWriteAPIKey);

            if (httpCode == 200) {
                Serial.printf("[ThingSpeak] Enviado — Temp: %.1f °C | Hum: %.1f %%\n",
                              temperatura, humedad);
            } else {
                Serial.printf("[ThingSpeak] Error HTTP: %d\n", httpCode);
            }
        } else {
            Serial.println("[ThingSpeak] Sin datos válidos aún, se omite el envío.");
        }
    }
}
