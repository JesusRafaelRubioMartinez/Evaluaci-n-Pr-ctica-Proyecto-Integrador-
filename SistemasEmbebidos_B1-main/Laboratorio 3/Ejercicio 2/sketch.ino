#include <math.h>

const int PIN_LED = 9;
float angulo = 0.0;

void setup() {
  pinMode(PIN_LED, OUTPUT);
}

void loop() {
  // sin() devuelve un valor entre -1.0 y 1.0. 
  // Lo mapeamos matemáticamente para que vaya de 0.0 a 1.0
  float seno = (sin(angulo) + 1.0) / 2.0;
  
  // Multiplicamos por 255 para obtener el nivel de brillo (0-255)
  int brillo = (int) (seno * 255); 
  
  analogWrite(PIN_LED, brillo);
  
  angulo += 0.05; // Velocidad del efecto
  
  // Reiniciamos el ciclo cuando da una vuelta completa (2*PI radianes)
  if (angulo > 2 * PI) angulo = 0;
  
  delay(15);
}