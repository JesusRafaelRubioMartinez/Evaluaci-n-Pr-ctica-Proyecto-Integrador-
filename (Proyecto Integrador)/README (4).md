# Manual de Diseño Electrónico y Sistemas Embebidos

**PROYECTO:** Prototipo para la Clasificación de Metales y Plásticos mediante Visión Artificial y Redes Neuronales
**MATERIA:** Diseño Electrónico basado en Sistemas Embebidos
**DOCENTE:** Daniel Lopez Piña
**INSTITUCIÓN:** Universidad Autónoma de Tamaulipas - Unidad Académica Multidisciplinaria Mante

---

## 1. Resumen del Sistema Embebido
El proyecto consiste en un sistema de clasificación automatizado que integra hardware mecánico, microcontroladores y lógica de procesamiento en tiempo real. El objetivo principal es la separación eficiente de residuos de aluminio y plástico mediante el accionamiento coordinado de actuadores basados en señales de control derivadas de un análisis de visión artificial.

---

## 2. Especificaciones de Hardware (Diseño Electrónico)

El sistema se basa en una arquitectura de control distribuida donde un microcontrolador gestiona los periféricos de salida.

### 2.1 Componentes Principales
| Componente | Función en el Sistema Embebido |
| :--- | :--- |
| **Arduino Uno (Rev3)** | Unidad de control local. Procesa comandos seriales y genera señales PWM para los servomotores. |
| **Servomotor SG90** | Actuador mecánico. Torque de 1.8 kg-cm. Posicionamiento angular preciso (0° - 180°). |
| **Cámara Web** | Sensor de adquisición de datos visuales (1080p). |
| **Fuente de Alimentación** | Suministro de 5V para el microcontrolador y corriente pico de ~650 mA para los actuadores. |
| **Interfaz Host (PC)** | Procesamiento de alto nivel (IA) y puente de comunicación UART. |

---

## 3. Firmware del Sistema (Arduino C++)

El firmware está diseñado para operar bajo un esquema de interrupción por disponibilidad de datos en el buffer serial. Utiliza la biblioteca `Servo.h` para el control de los actuadores.

### 3.1 Lógica de Control de Actuadores
El código implementa una secuencia de dos fases para asegurar la correcta disposición del residuo:

```cpp
#include <Servo.h>
#include <Arduino.h>

// DECLARACIÓN DE SERVOS Y PINES
Servo servoClasificacion; 
Servo servoTrampilla1;
Servo servoTrampilla2;

int pinClasificacion = 2;
int pinTrampilla1 = 3;
int pinTrampilla2 = 4;

void setup() {
  Serial.begin(9600); // Comunicación UART
  servoClasificacion.attach(pinClasificacion);
  servoTrampilla1.attach(pinTrampilla1);
  servoTrampilla2.attach(pinTrampilla2);
  
  // Posiciones iniciales de seguridad
  servoClasificacion.write(45);
  servoTrampilla1.write(180);
  servoTrampilla2.write(0);
  delay(2000);
}

void loop() {
  if (Serial.available() > 0) {
    char comando = Serial.read(); // Recepción de instrucción ASCII
    
    if (comando == 'A' || comando == 'P') {
      // FASE 1: POSICIONAMIENTO DE CLASIFICACIÓN
      if (comando == 'A') {
        for (int ang = 45; ang <= 140; ang++) {
          servoClasificacion.write(ang);
          delay(20);
        }
      } else {
        for (int ang = 45; ang <= 140; ang++) {
          servoClasificacion.write(ang);
          delay(20);
        }
      }
      delay(2000);
      
      // FASE 2: ACTIVACIÓN SINCRONIZADA DE TRAMPILLAS
      for (int i = 0; i <= 45; i++) {
        servoTrampilla1.write(180 - i);
        servoTrampilla2.write(0 + i);
        delay(20);
      }
      delay(2000); // Tiempo de descarga
      
      // CIERRE DE SISTEMA
      for (int i = 45; i >= 0; i--) {
        servoTrampilla1.write(180 - i);
        servoTrampilla2.write(0 + i);
        delay(20);
      }
    }
  }
}
