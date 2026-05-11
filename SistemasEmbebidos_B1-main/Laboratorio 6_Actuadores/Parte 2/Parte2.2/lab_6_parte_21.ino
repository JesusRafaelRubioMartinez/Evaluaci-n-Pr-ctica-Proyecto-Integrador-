#include <Servo.h>

Servo mi_servo;
const int PIN_SERVO = 11;
const int PIN_POT = A0;
const int ENA = 5; 
const int IN1 = 8;
const int IN2 = 9;

int angulo_anterior = -1;

void setup() {
  mi_servo.attach(PIN_SERVO);
  mi_servo.write(90);

  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);


  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  Serial.begin(9600);
  Serial.println("Sistema unificado listo.");
}

void loop() {

  int pot_val = analogRead(PIN_POT);

  int angulo = map(pot_val, 0, 1023, 0, 180);
  if (abs(angulo - angulo_anterior) >= 2) {
    mi_servo.write(angulo);
    angulo_anterior = angulo;
  }


  int velocidad = map(pot_val, 0, 1023, 0, 255);
  analogWrite(ENA, velocidad);

  delay(20);
}