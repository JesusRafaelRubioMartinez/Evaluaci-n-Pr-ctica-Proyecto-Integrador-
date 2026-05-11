// Lab01 Blink.ino
/* ======================================================
   Lab 01 – Blink: Patron SOS en codigo morse
   Pin de salida: 13 (LED integrado o externo)
   ====================================================== */

const int PIN_LED = 13;        
int contador = 0;              

// Funcion para hacer un destello
void destello(int tiempo) {

  contador++;

  digitalWrite(PIN_LED, HIGH);
  Serial.print("[#");
  Serial.print(contador);
  Serial.println("] LED -> ENCENDIDO");
  delay(tiempo);

  digitalWrite(PIN_LED, LOW);
  Serial.print("[#");
  Serial.print(contador);
  Serial.println("] LED -> APAGADO");
  delay(200); // pausa corta entre destellos
}

void setup() {

  pinMode(PIN_LED, OUTPUT);

  Serial.begin(9600);
  Serial.println("=== Lab SOS Morse ===");
}

void loop() {

  // --- 3 cortos ---
  destello(200);
  destello(200);
  destello(200);

  // --- 3 largos ---
  destello(600);
  destello(600);
  destello(600);

  // --- 3 cortos ---
  destello(200);
  destello(200);
  destello(200);

  // pausa entre repeticiones (2 segundos)
  Serial.println("---- PAUSA ----");
  delay(2000);
}