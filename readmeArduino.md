#include <AccelStepper.h>

// Configurações do Motor Vertical (Altitude)
#define PUL_VERT 2
#define DIR_VERT 3
// Configurações do Motor Horizontal (Azimute)
#define PUL_HORIZ 7
#define DIR_HORIZ 9

const float MICROSTEPS = 125.0;
const float STEPS_PER_REV = 25000.0; // Como você mencionou
const float STEPS_PER_DEGREE_AZ = (STEPS_PER_REV) / 360.0;
const float STEPS_PER_DEGREE_ALT = (STEPS_PER_REV) / 360.0; // Sem redução mecânica


// Taxas de Movimento Astronômicas (aproximadas) - Podem ser úteis para rastreamento, mas não são usadas neste código
const float EARTH_ROTATION_RATE = 0.00417; // graus por segundo
const float LUNA_MOVEMENT_RATE = 0.0002; // graus por segundo (exemplo)


AccelStepper motorVert(AccelStepper::DRIVER, PUL_VERT, DIR_VERT);
AccelStepper motorHoriz(AccelStepper::DRIVER, PUL_HORIZ, DIR_HORIZ);

void setup() {
  Serial.begin(115200);

  // Configurações da AccelStepper (ajuste conforme necessário)
  motorHoriz.setMaxSpeed(5);    // Exemplo: ajuste para o seu hardware
  motorHoriz.setAcceleration(0.2); // Exemplo: ajuste para o seu hardware
  motorVert.setMaxSpeed(5);      // Exemplo: ajuste para o seu hardware
  motorVert.setAcceleration(0.2);   // Exemplo: ajuste para o seu hardware


  motorVert.setCurrentPosition(0);
  motorHoriz.setCurrentPosition(0);

  // Define a direção inicial do motor (ajuste conforme necessário)
  digitalWrite(DIR_HORIZ, HIGH); // ou LOW, dependendo da sua montagem
  digitalWrite(DIR_VERT, HIGH); // ou LOW, dependendo da sua montagem

  Serial.println("Sistema de rastreamento pronto. Aguardando comandos...");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.startsWith("POS,")) {
      int commaPos = input.indexOf(',', 4);
      float newAlt = input.substring(4, commaPos).toFloat();
      float newAzi = input.substring(commaPos + 1).toFloat();

      Serial.print("Recebido -> Alt: "); Serial.print(newAlt);
      Serial.print("° | Azi: "); Serial.println(newAzi);

    long targetAziSteps = newAzi * STEPS_PER_DEGREE_AZ;
    long targetAltSteps = newAlt * STEPS_PER_DEGREE_ALT;

    Serial.print("newAzi: ");
Serial.println(newAzi);
Serial.print("STEPS_PER_DEGREE_AZ: ");
Serial.println(STEPS_PER_DEGREE_AZ);
Serial.print("targetAziSteps: ");
Serial.println(targetAziSteps);

    // Calcula os limites máximos em passos
    long maxAziSteps = 360.0 * STEPS_PER_DEGREE_AZ; // Limite máximo para Azimute
    long maxAltSteps = 360.0 * STEPS_PER_DEGREE_ALT; // Limite máximo para Altitude (considerando a redução)

      if (abs(targetAziSteps) <= maxAziSteps && abs(targetAltSteps) <= maxAltSteps) { // Limites ajustados para a redução

        // Movimento do Azimute (com velocidade gradual)
        motorHoriz.moveTo(targetAziSteps);
        while (motorHoriz.distanceToGo() != 0) { motorHoriz.run(); }


        // Movimento da Altitude (com velocidade gradual)
        motorVert.moveTo(targetAltSteps);
        while (motorVert.distanceToGo() != 0) { motorVert.run(); }



        float currentAzi = motorHoriz.currentPosition() / STEPS_PER_DEGREE_AZ;
        float currentAlt = motorVert.currentPosition() / STEPS_PER_DEGREE_ALT;

        Serial.print("Posição atingida -> Alt: "); Serial.print(currentAlt);
        Serial.print("° | Azi: "); Serial.println(currentAzi);

        if (abs(newAzi - currentAzi) <= TOLERANCE && abs(newAlt - currentAlt) <= TOLERANCE) {
          Serial.println("Posição atingida (dentro da tolerância)!");
          motorHoriz.stop(); motorHoriz.disableOutputs();
          motorVert.stop(); motorVert.disableOutputs();
        } else {
          Serial.println("Posição não atingida (fora da tolerância)!");
        }

      } else {
        Serial.println("Erro: Posição fora dos limites!");
      }
    } else if (input.startsWith("SPEED,")) {
      // ... (seu código para controle de velocidade com STEPS_PER_DEGREE_AZ e STEPS_PER_DEGREE_ALT)
    } else if (input == "STOP") {
      motorVert.stop(); motorVert.disableOutputs();
      motorHoriz.stop(); motorHoriz.disableOutputs();
      Serial.println("Parada de emergência!");
    }
  }
}