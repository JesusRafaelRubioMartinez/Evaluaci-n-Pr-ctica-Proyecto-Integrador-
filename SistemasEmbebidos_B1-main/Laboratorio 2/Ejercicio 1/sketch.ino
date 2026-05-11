// Definición de pines
const int PIN_BOTON_CONT = 2;
const int PIN_BOTON_RES = 3;
const int PIN_LED = 13;

int contador = 0;

// Variables para recordar cómo estaban los botones antes
int estadoAnteriorCont = HIGH;
int estadoAnteriorRes  = HIGH;

void setup() { 
    // Configuramos ambos botones con la resistencia interna
    pinMode(PIN_BOTON_CONT, INPUT_PULLUP); 
    pinMode(PIN_BOTON_RES,  INPUT_PULLUP); 
    pinMode(PIN_LED,        OUTPUT); 
    
    Serial.begin(9600); 
    Serial.println("Sistema iniciado. Contador en: 0"); 
} 

void loop() { 
    // Leemos el estado actual de los dos botones
    int lecturaCont = digitalRead(PIN_BOTON_CONT); 
    int lecturaRes  = digitalRead(PIN_BOTON_RES); 

    if (lecturaCont == LOW && estadoAnteriorCont == HIGH) { 
        delay(50); // Pequeña pausa para eliminar el rebote mecánico
        contador++; 
        
        Serial.print("Contador: "); 
        Serial.println(contador); 
        
        // Encendemos el LED brevemente para confirmar visualmente
        digitalWrite(PIN_LED, HIGH);
        delay(100);
        digitalWrite(PIN_LED, LOW);
    } 
    estadoAnteriorCont = lecturaCont; // Guardamos el estado para el siguiente ciclo


    // --- LÓGICA DEL BOTÓN RESET ---
    // Si el botón reset está presionado (LOW) y antes no lo estaba (HIGH)
    if (lecturaRes == LOW && estadoAnteriorRes == HIGH) { 
        delay(50); // Pausa para el rebote
        contador = 0; 
        
        Serial.println("CONTEO REINICIADO"); 
        
        // Hacemos parpadear el LED dos veces para confirmar el reset
        for(int i = 0; i < 2; i++) {
            digitalWrite(PIN_LED, HIGH);
            delay(100);
            digitalWrite(PIN_LED, LOW);
            delay(100);
        }
    } 
    estadoAnteriorRes = lecturaRes; // Guardamos el estado para el siguiente ciclo
}