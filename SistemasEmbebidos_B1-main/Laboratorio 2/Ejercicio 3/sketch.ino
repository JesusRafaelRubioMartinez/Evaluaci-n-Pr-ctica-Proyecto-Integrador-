// Definición de pines
const int PIN_BOTON_CONT = 2; // Botón original (Suma)
const int PIN_BOTON_RES  = 3; // Botón nuevo (Reinicia)
const int PIN_LED        = 13; // Tu LED indicador

int contador = 0;

// Variables para el anti-rebote (debounce)
int estadoAnteriorCont = HIGH;
int estadoAnteriorRes  = HIGH;

void setup() { 
    pinMode(PIN_BOTON_CONT, INPUT_PULLUP); 
    pinMode(PIN_BOTON_RES,  INPUT_PULLUP); 
    pinMode(PIN_LED,        OUTPUT); 
    
    Serial.begin(9600); 
    Serial.println("Ejercicio 2: Parpadeo proporcional al contador"); 
} 

void loop() { 
    int lecturaCont = digitalRead(PIN_BOTON_CONT); 
    int lecturaRes  = digitalRead(PIN_BOTON_RES); 

    // --- LÓGICA DEL BOTÓN CONTADOR ---
    if (lecturaCont == LOW && estadoAnteriorCont == HIGH) { 
        delay(50); // Anti-rebote
        contador++; 
        
        Serial.print("Pulsaciones: "); 
        Serial.println(contador); 
        
        // El ciclo 'for' ejecutará el parpadeo 'contador' veces
        for (int i = 0; i < contador; i++) {
            digitalWrite(PIN_LED, HIGH); // Prende
            delay(250);                  // Espera un cuarto de segundo
            digitalWrite(PIN_LED, LOW);  // Apaga
            delay(250);                  // Espera un cuarto de segundo antes del siguiente
        }
    } 
    estadoAnteriorCont = lecturaCont; 


    // --- LÓGICA DEL BOTÓN RESET ---
    if (lecturaRes == LOW && estadoAnteriorRes == HIGH) { 
        delay(50); 
        contador = 0; 
        
        Serial.println("CONTEO REINICIADO"); 
        
        // Un parpadeo largo para indicar que se reinició
        digitalWrite(PIN_LED, HIGH);
        delay(800);
        digitalWrite(PIN_LED, LOW);
    } 
    estadoAnteriorRes = lecturaRes; 
}