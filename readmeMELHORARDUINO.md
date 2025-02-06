#include <AccelStepper.h>

// Definição dos pinos
#define PUL_AZ 7
#define DIR_AZ 9
#define PUL_ALT 2
#define DIR_ALT 3

// Configuração dos motores
AccelStepper motorAz(AccelStepper::DRIVER, PUL_AZ, DIR_AZ);
AccelStepper motorAlt(AccelStepper::DRIVER, PUL_ALT, DIR_ALT);

// Constantes de passos
const int passos_por_revolucao = 3200;  // Passos por revolução do motor

// Ajuste para os passos por grau
const float passos_por_grau_azimute = (float)passos_por_revolucao / 360.0;  
const float passos_por_grau_altitude = (float)passos_por_revolucao / 90.0;  

// Velocidade angular da Lua no céu (~0,5° por minuto)
const float velocidade_angular_lua = 0.5 / 60.0;  // Graus por segundo

void setup() {
  Serial.begin(115200);

  // Ajuste de velocidade máxima e aceleração para movimento suave
  motorAz.setMaxSpeed(50);  // Velocidade ajustada para movimento suave
  motorAz.setAcceleration(10);  // Aceleração mais baixa para evitar ultrapassagens

  motorAlt.setMaxSpeed(50);  // Velocidade ajustada para movimento suave
  motorAlt.setAcceleration(10);  // Aceleração mais baixa para evitar ultrapassagens
}

void loop() {
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    Serial.print("Comando recebido: ");
    Serial.println(comando);  // Log do comando recebido

    // Verifica se o comando começa com "POS,"
    if (comando.startsWith("POS,")) {
      // Remove o prefixo "POS,"
      comando = comando.substring(4);

      // Divide o restante do comando em azimute e altitude
      int separador = comando.indexOf(',');
      if (separador == -1) {
        Serial.println("Erro: Comando inválido (falta vírgula)");
        return;
      }

      String azimute_str = comando.substring(0, separador);
      String altitude_str = comando.substring(separador + 1);

      Serial.print("Azimute string: ");
      Serial.println(azimute_str);  // Log da string do azimute
      Serial.print("Altitude string: ");
      Serial.println(altitude_str);  // Log da string da altitude

      float azimute = azimute_str.toFloat();
      float altitude = altitude_str.toFloat();

      Serial.print("Azimute float: ");
      Serial.print(azimute);
      Serial.print(", Altitude float: ");
      Serial.println(altitude);  // Log dos valores convertidos

      // Cálculo de passos com base nos novos valores de micropassos
      long azimute_passos = azimute * passos_por_grau_azimute;
      long altitude_passos = altitude * passos_por_grau_altitude;

      Serial.print("Passos Azimute: ");
      Serial.print(azimute_passos);
      Serial.print(", Passos Altitude: ");
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
    } else {
      Serial.println("Erro: Comando inválido (não começa com 'POS,')");
    }
  }
}