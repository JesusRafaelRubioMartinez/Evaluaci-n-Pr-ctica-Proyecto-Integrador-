const int PIN_BOTON_1 = 2; // Botón de conteo
const int PIN_BOTON_2 = 3; // Botón de reset
const int PIN_LED = 13;
const unsigned long DEBOUNCE_MS = 20;

int conteo = 0;

// Variables para el Botón 1
int estado_btn_1 = HIGH;
int ultimo_estado_1 = HIGH;
unsigned long t_cambio_1 = 0;

// Variables para el Botón 2
int estado_btn_2 = HIGH;
int ultimo_estado_2 = HIGH;
unsigned long t_cambio_2 = 0;

void setup() {
  pinMode(PIN_BOTON_1, INPUT_PULLUP);
  pinMode(PIN_BOTON_2, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  Serial.begin(9600);
  Serial.println("Ejercicios 1 y 2: Sistema listo");
}

void loop() {
  // --------------------------------------------------
  // 1. Lógica del Botón de Conteo (Ejercicio 2)
  // --------------------------------------------------
  int lectura_1 = digitalRead(PIN_BOTON_1);
  
  if (lectura_1 != ultimo_estado_1) {
    t_cambio_1 = millis(); // Reinicia el temporizador si hay ruido/rebote
  }
  
  if ((millis() - t_cambio_1) > DEBOUNCE_MS) {
    // Si el estado ya es estable y es diferente al que teníamos guardado:
    if (lectura_1 != estado_btn_1) {
      estado_btn_1 = lectura_1;
      
      if (estado_btn_1 == LOW) { // LOW significa que el botón fue presionado
        conteo++;
        Serial.print("Pulsacion #");
        Serial.println(conteo);
        
        // Parpadear el LED "N" veces según el conteo
        for(int i = 0; i < conteo; i++) {
          digitalWrite(PIN_LED, HIGH);
          delay(200);
          digitalWrite(PIN_LED, LOW);
          delay(200);
        }
      }
    }
  }
  ultimo_estado_1 = lectura_1;

  // --------------------------------------------------
  // 2. Lógica del Botón de Reinicio (Ejercicio 1)
  // --------------------------------------------------
  int lectura_2 = digitalRead(PIN_BOTON_2);
  
  if (lectura_2 != ultimo_estado_2) {
    t_cambio_2 = millis();
  }
  
  if ((millis() - t_cambio_2) > DEBOUNCE_MS) {
    if (lectura_2 != estado_btn_2) {
      estado_btn_2 = lectura_2;
      
      if (estado_btn_2 == LOW) { // Se presionó el botón de reset
        conteo = 0;
        Serial.println("CONTEO REINICIADO");
      }
    }
  }
  ultimo_estado_2 = lectura_2;
}