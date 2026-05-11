// Lab01 Blink.ino
/* ======================================================
   Lab 01 – SOS con millis()
   Pin de salida: 13
   ====================================================== */

const int PIN_LED = 13;
int contador = 0;


// Funcion para hacer un destello
void destello(int tiempo) {

  contador++;

  // ENCENDER
  digitalWrite(PIN_LED, HIGH);
  Serial.print("[#");
  Serial.print(contador);
  Serial.print("] t = ");
  Serial.print(millis());
  Serial.println(" ms LED -> ENCENDIDO");

  delay(tiempo);

  // APAGAR
  digitalWrite(PIN_LED, LOW);
  Serial.print("[#");
  Serial.print(contador);
  Serial.print("] t = ");
  Serial.print(millis());
  Serial.println(" ms LED -> APAGADO");

  delay(200); // pausa corta entre destellos
}


void setup() {

  pinMode(PIN_LED, OUTPUT);

  Serial.begin(9600);
  Serial.println("=== Lab SOS Morse con millis ===");
}


void loop() {

  // 3 cortos
  destello(200);
  destello(200);
  destello(200);

  // 3 largos
  destello(600);
  destello(600);
  destello(600);

  // 3 cortos
  destello(200);
  destello(200);
  destello(200);

  // pausa de 2 segundos
  Serial.println("---- PAUSA ----");
  delay(2000);
}