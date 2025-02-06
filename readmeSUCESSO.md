#include <AccelStepper.h>

// Definição dos pinos
#define PUL_AZ 7
#define DIR_AZ 9
#define PUL_ALT 2
#define DIR_ALT 3

// Configuração dos motores
AccelStepper motorAz(AccelStepper::DRIVER, PUL_AZ, DIR_AZ);
AccelStepper motorAlt(AccelStepper::DRIVER, PUL_ALT, DIR_ALT);

// Nova constante para 3200 passos/rev
const int passos_por_revolucao = 3200;  

// Ajuste para os passos por grau
const float passos_por_grau_azimute = (float)passos_por_revolucao / 360.0;  
const float passos_por_grau_altitude = (float)passos_por_revolucao / 90.0;  

// Velocidade angular da Lua no céu (~0,5° por minuto)
const float velocidade_angular_lua = 0.5 / 60.0;  // Graus por segundo

void setup() {
  Serial.begin(115200);

  // Ajuste de velocidade máxima e aceleração para um movimento mais suave
  motorAz.setMaxSpeed(60);  // Teste valores entre 10-50 para suavidade
  motorAz.setAcceleration(10);  

  motorAlt.setMaxSpeed(60);  
  motorAlt.setAcceleration(10);  
}

void loop() {
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    int separador = comando.indexOf(',');
    String azimute_str = comando.substring(0, separador);
    String altitude_str = comando.substring(separador + 1);
    
    float azimute = azimute_str.toFloat();
    float altitude = altitude_str.toFloat();
    
    // Cálculo de passos com base nos novos valores de micropassos
    long azimute_passos = azimute * passos_por_grau_azimute;
    long altitude_passos = altitude * passos_por_grau_altitude;

    Serial.print("Azimute: ");
    Serial.print(azimute);
    Serial.print("°, Passos para Azimute: ");
    Serial.println(azimute_passos);
    
    Serial.print("Altitude: ");
    Serial.print(altitude);
    Serial.print("°, Passos para Altitude: ");
    Serial.println(altitude_passos);

    // Move os motores para a posição desejada
    motorAz.moveTo(azimute_passos);
    motorAlt.moveTo(altitude_passos);

    // Executa o movimento suavemente
    while (motorAz.distanceToGo() != 0 || motorAlt.distanceToGo() != 0) {
      motorAz.run();
      motorAlt.run();
    }

    // Delay para rastreamento contínuo baseado na velocidade da Lua
    float delay_ms = (1.0 / velocidade_angular_lua) * 1000;  // Tempo para cada grau
    delay(delay_ms);  
  }
}