#include <Servo.h>
#include <Arduino.h>

// ==========================================
// DECLARACIÓN DE SERVOS Y PINES
// ==========================================
Servo servoClasificacion; // Fase 1
Servo servoTrampilla1;    // Fase 2 (Inicia en 180)
Servo servoTrampilla2;    // Fase 2 (Inicia en 0)

int pinClasificacion = 2; 
int pinTrampilla1 = 3; 
int pinTrampilla2 = 4; 

void setup() {
  // 1. INICIAMOS LA COMUNICACIÓN SERIAL (Debe coincidir con Python)
  Serial.begin(9600);

  servoClasificacion.attach(pinClasificacion);
  servoTrampilla1.attach(pinTrampilla1);
  servoTrampilla2.attach(pinTrampilla2);

  // Posiciones iniciales de todos los servos antes de empezar
  servoClasificacion.write(45);
  servoTrampilla1.write(180);
  servoTrampilla2.write(0);

  // Tiempo para que todos se acomoden al inicio
  delay(2000); 
}

void loop() {
  // 2. VERIFICAMOS SI PYTHON ENVIÓ UN DATO
  if (Serial.available() > 0) {
    char comando = Serial.read(); // Leemos el carácter recibido

    // Si es Aluminio o Plástico, iniciamos la secuencia
    if (comando == 'A' || comando == 'P') {
      
      // ==========================================
      // FASE 1: CLASIFICACIÓN
      // ==========================================
      
      if (comando == 'A') {
        Serial.println("Aluminio detectado!");
        // Movimiento para ALUMINIO (45 a 140)
        for (int ang = 45; ang <= 140; ang++) {
          servoClasificacion.write(ang);
          delay(20);
        }
      } 
      else if (comando == 'P') {
        Serial.println("Plástico detectado!");
        // Movimiento para PLÁSTICO (Aquí puedes cambiar los ángulos si 
        // necesitas que gire hacia el lado contrario, por ej: 45 a 0)
        // Por ahora mantenemos tu movimiento original:
        for (int ang = 45; ang <= 140; ang++) {
          servoClasificacion.write(ang);
          delay(20);
        }
      }
      
      // 2 segundos en la posición de clasificación
      delay(2000);
      
      // Movimiento de regreso (140 a 45)
      for (int ang = 140; ang >= 45; ang--) {
        servoClasificacion.write(ang);
        delay(20);
      }
      
      // 2 segundos de espera antes de activar las trampillas
      delay(2000);

      // ==========================================
      // FASE 2: ACTIVACIÓN DE TRAMPILLAS (SIMULTÁNEO)
      // ==========================================
      
      // Movimiento de apertura sincronizado
      for (int i = 0; i <= 45; i++) {
        servoTrampilla1.write(180 - i); // Baja de 180 a 135
        servoTrampilla2.write(0 + i);   // Sube de 0 a 45
        delay(20); // Movimiento suave
      }
      
      // 2 segundos de espera con las trampillas abiertas para que caiga la pieza
      delay(2000);
      
      // Movimiento de cierre sincronizado
      for (int i = 45; i >= 0; i--) {
        servoTrampilla1.write(180 - i); // Sube de 135 a 180
        servoTrampilla2.write(0 + i);   // Baja de 45 a 0
        delay(20); 
      }
      
      // 2 segundos de espera con las trampillas cerradas antes de reiniciar
      delay(2000);
    }
  }
}