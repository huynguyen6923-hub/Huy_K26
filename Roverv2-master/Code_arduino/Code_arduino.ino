#include <Adafruit_PWMServoDriver.h>

// Buffer for commands
String inputBuffer = "";

// Driver Front (L298 #1): FL = Out1 (ENA), FR = Out2 (ENB)
// Động cơ phía trước bên trái (Driver Front, Output 1)
#define PWM_FL 12
#define IN1_FL 24
#define IN2_FL 25

// Động cơ phía trước bên phải (Driver Front, Output 2)
#define PWM_FR 11
#define IN1_FR 27
#define IN2_FR 26

// Driver Middle (L298 #2): ML = Out1 (ENA), MR = Out2 (ENB)
// Động cơ giữa bên trái — IN1/IN2 swapped to invert direction (motor leads reversed)
#define PWM_ML 10
#define IN1_ML 30
#define IN2_ML 31

// Động cơ giữa bên phải — IN1/IN2 swapped to invert direction (motor leads reversed)
#define PWM_MR 9
#define IN1_MR 33
#define IN2_MR 32

// Driver Back (L298 #3): BL = Out1 (ENA), BR = Out2 (ENB)
// Động cơ phía sau bên trái — IN1/IN2 swapped to invert direction (motor leads reversed)
#define PWM_BL 8
#define IN1_BL 50
#define IN2_BL 51

// Động cơ phía sau bên phải
#define PWM_BR 7
#define IN1_BR 53
#define IN2_BR 52

// Sai số bù trừ servo
int fr_ofst = 0;
int mr_ofst = 0;
int br_ofst = 0;
int fl_ofst = 0;
int ml_ofst = 0;
int bl_ofst = 0;

// Vị trí bắt đầu servo
int start_angle = 90;

// Tốc độ động cơ DC (JGA25-370 130rpm)
// PWM 0-255, default 200 (~78%)
int globalSpeed = 200;
#define MOTOR_MIN_PWM 80   // Dưới ngưỡng này motor không quay
#define MOTOR_MAX_PWM 255

// Khai báo PCA9685
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVOMIN  150  // Giá trị PWM cho 0 độ
#define SERVOMAX  600  // Giá trị PWM cho 180 độ

void setup() {
  Serial.begin(9600);

  // Thiết lập cho phía trước bên trái
  pinMode(PWM_FL, OUTPUT);
  pinMode(IN1_FL, OUTPUT);
  pinMode(IN2_FL, OUTPUT);

  // Thiết lập cho giữa bên trái
  pinMode(PWM_ML, OUTPUT);
  pinMode(IN1_ML, OUTPUT);
  pinMode(IN2_ML, OUTPUT);

  // Thiết lập cho phía sau bên trái
  pinMode(PWM_BL, OUTPUT);
  pinMode(IN1_BL, OUTPUT);
  pinMode(IN2_BL, OUTPUT);

  // Thiết lập cho phía trước bên phải
  pinMode(PWM_FR, OUTPUT);
  pinMode(IN1_FR, OUTPUT);
  pinMode(IN2_FR, OUTPUT);

  // Thiết lập cho giữa bên phải
  pinMode(PWM_MR, OUTPUT);
  pinMode(IN1_MR, OUTPUT);
  pinMode(IN2_MR, OUTPUT);

  // Thiết lập cho phía sau bên phải
  pinMode(PWM_BR, OUTPUT);
  pinMode(IN1_BR, OUTPUT);
  pinMode(IN2_BR, OUTPUT);

  // Khởi tạo PCA9685
  pwm.begin();
  pwm.setPWMFreq(50);

  // Set vị trí khởi đầu cho servo
  // Block 1 LEFT: CH0=FL, CH1=ML, CH2=BL | Block 2 RIGHT: CH4=FR, CH5=MR, CH6=BR
  Serial.println("Setting servo to 90 degrees");
  setServoAngle(0, start_angle + fl_ofst);  // Kênh 0: FL
  setServoAngle(1, start_angle + ml_ofst);  // Kênh 1: ML
  setServoAngle(2, start_angle + bl_ofst);  // Kênh 2: BL
  // CH3 skipped
  setServoAngle(4, start_angle + fr_ofst);  // Kênh 4: FR
  setServoAngle(5, start_angle + mr_ofst);  // Kênh 5: MR
  setServoAngle(6, start_angle + br_ofst);  // Kênh 6: BR
}

unsigned long lastCharTime = 0;

void loop() {
  // Clear buffer if no data received for 500ms (prevents stuck buffer)
  if (inputBuffer.length() > 0 && millis() - lastCharTime > 500) {
    inputBuffer = "";
  }

  while (Serial.available() > 0) {
    char c = Serial.read();
    lastCharTime = millis();

    // Skip null characters
    if (c == 0) continue;

    // Buffer all characters until newline
    if (c == '\n' || c == '\r') {
      if (inputBuffer.length() > 0) {
        // Check if it's a single character command
        if (inputBuffer.length() == 1) {
          char cmd = inputBuffer.charAt(0);
          if (cmd == 'W' || cmd == 'S' || cmd == 'H' || cmd == 'Q' || cmd == 'E' ||
              cmd == 'A' || cmd == 'D' || cmd == 'R' || cmd == 'F' || cmd == 'K' ||
              cmd == 'U' || cmd == 'O' || cmd == 'J' || cmd == 'L') {
            processSingleChar(cmd);
          }
        } else {
          // Multi-character command
          processCommand(inputBuffer);
        }
      }
      inputBuffer = "";  // Always clear on newline
    } else {
      if (inputBuffer.length() < 15) {
        inputBuffer += c;
      }
    }
  }
}

void processSingleChar(char cmd) {
  Serial.print("CMD: ");
  Serial.println(cmd);

  switch (cmd) {
    case 'W': forward(); break;
    case 'S': reverse(); break;
    case 'H': stopMotor(); break;
    case 'A': crableft(); break;
    case 'D': crabright(); break;
    case 'L': smallRight(); break;
    case 'J': smallLeft(); break;
    case 'R': diagonalRight(); break;
    case 'F': diagonalLeft(); break;
    case 'K': center(); break;
    case 'Q': rotateleft(); break;
    case 'E': rotateright(); break;
    case 'U': bigLeft(); break;
    case 'O': bigRight(); break;
  }
}

void processCommand(String cmd) {
  cmd.trim();
  Serial.print("CMD: ");
  Serial.println(cmd);

  int colonIndex = cmd.indexOf(':');
  if (colonIndex > 0) {
    String channelStr = cmd.substring(0, colonIndex);
    String valueStr = cmd.substring(colonIndex + 1);

    // ========== GLOBAL SPEED COMMAND ==========
    // Format: "SPD:150" (set global speed 0-255)
    if (channelStr == "SPD") {
      globalSpeed = constrain(valueStr.toInt(), 0, MOTOR_MAX_PWM);
      Serial.print("Global speed -> "); Serial.println(globalSpeed);
      return;
    }

    // ========== SERVO OFFSET COMMAND ==========
    // Format: "OFST:0:3" (set channel 0 offset to 3)
    if (channelStr == "OFST") {
      int ofstColon = valueStr.indexOf(':');
      if (ofstColon > 0) {
        int ofstCh = valueStr.substring(0, ofstColon).toInt();
        int ofstVal = valueStr.substring(ofstColon + 1).toInt();
        ofstVal = constrain(ofstVal, -45, 45);
        switch (ofstCh) {
          case 0: fl_ofst = ofstVal; break;
          case 1: ml_ofst = ofstVal; break;
          case 2: bl_ofst = ofstVal; break;
          case 4: fr_ofst = ofstVal; break;
          case 5: mr_ofst = ofstVal; break;
          case 6: br_ofst = ofstVal; break;
        }
        Serial.print("Offset CH"); Serial.print(ofstCh);
        Serial.print(" -> "); Serial.println(ofstVal);
      }
      return;
    }

    // ========== INDIVIDUAL DC MOTOR COMMANDS ==========
    // Format: "FL:1" (forward at globalSpeed), "FL:-1:150" (reverse at speed 150), "FL:0" (stop)
    // Motors: FL, ML, BL, FR, MR, BR
    // Direct pin mapping: code labels = physical positions
    // Driver Front  (24-27, PWM 12/11): FL=Out1(ENA=12), FR=Out2(ENB=11)
    // Driver Middle (28-31, PWM 10/9): ML=Out1(ENA=10), MR=Out2(ENB=9)
    // Driver Back   (50-53, PWM 8/7):  BL=Out1(ENA=8),  BR=Out2(ENB=7)

    // Parse direction and optional speed: "dir" or "dir:speed"
    int motorDir = 0;
    int motorSpeed = 0;
    int secondColon = valueStr.indexOf(':');
    if (secondColon > 0) {
      motorDir = valueStr.substring(0, secondColon).toInt();
      motorSpeed = valueStr.substring(secondColon + 1).toInt();
      motorSpeed = constrain(motorSpeed, 0, MOTOR_MAX_PWM);
    } else {
      motorDir = valueStr.toInt();
      motorSpeed = globalSpeed;
    }
    motorDir = constrain(motorDir, -1, 1);
    if (motorDir == 0) motorSpeed = 0;

    if (channelStr == "FL") {
      Serial.print("Motor FL -> dir:"); Serial.print(motorDir); Serial.print(" spd:"); Serial.println(motorSpeed);
      setMotor(motorDir, motorSpeed, PWM_FL, IN1_FL, IN2_FL);
      return;
    }
    if (channelStr == "ML") {
      Serial.print("Motor ML -> dir:"); Serial.print(motorDir); Serial.print(" spd:"); Serial.println(motorSpeed);
      setMotor(motorDir, motorSpeed, PWM_ML, IN1_ML, IN2_ML);
      return;
    }
    if (channelStr == "BL") {
      Serial.print("Motor BL -> dir:"); Serial.print(motorDir); Serial.print(" spd:"); Serial.println(motorSpeed);
      setMotor(motorDir, motorSpeed, PWM_BL, IN1_BL, IN2_BL);
      return;
    }
    if (channelStr == "FR") {
      Serial.print("Motor FR -> dir:"); Serial.print(motorDir); Serial.print(" spd:"); Serial.println(motorSpeed);
      setMotor(motorDir, motorSpeed, PWM_FR, IN1_FR, IN2_FR);
      return;
    }
    if (channelStr == "MR") {
      Serial.print("Motor MR -> dir:"); Serial.print(motorDir); Serial.print(" spd:"); Serial.println(motorSpeed);
      setMotor(motorDir, motorSpeed, PWM_MR, IN1_MR, IN2_MR);
      return;
    }
    if (channelStr == "BR") {
      Serial.print("Motor BR -> dir:"); Serial.print(motorDir); Serial.print(" spd:"); Serial.println(motorSpeed);
      setMotor(motorDir, motorSpeed, PWM_BR, IN1_BR, IN2_BR);
      return;
    }

    // ========== SERVO COMMANDS ==========
    // Format: "0:90" (channel:angle) or "*:90" (all servos)
    int angle = valueStr.toInt();
    angle = constrain(angle, 0, 180);

    // "*:angle" = All servos
    if (channelStr == "*") {
      Serial.print("All servos -> ");
      Serial.println(angle);
      // Block 1 LEFT: CH0-2, Block 2 RIGHT: CH4-6 (skip CH3, CH7)
      for (int ch = 0; ch <= 2; ch++) {
        setServoAngle(ch, angle);
      }
      for (int ch = 4; ch <= 6; ch++) {
        setServoAngle(ch, angle);
      }
      return;
    }

    // "0:angle" to "6:angle" = Individual servo (CH3 and CH7 unused)
    int channel = channelStr.toInt();
    if (channel >= 0 && channel <= 6 && channel != 3) {
      Serial.print("Servo ");
      Serial.print(channel);
      Serial.print(" -> ");
      Serial.println(angle);
      setServoAngle(channel, angle);
    }
  }
}

// Lệnh W(Tiến lên)
void forward() {
  setMotor(1, globalSpeed, PWM_FL, IN1_FL, IN2_FL);
  setMotor(1, globalSpeed, PWM_ML, IN1_ML, IN2_ML);
  setMotor(1, globalSpeed, PWM_BL, IN1_BL, IN2_BL);
  setMotor(1, globalSpeed, PWM_FR, IN1_FR, IN2_FR);
  setMotor(1, globalSpeed, PWM_MR, IN1_MR, IN2_MR);
  setMotor(1, globalSpeed, PWM_BR, IN1_BR, IN2_BR);
}

// Lệnh S(Lùi xuống)
void reverse() {
  setMotor(-1, globalSpeed, PWM_FL, IN1_FL, IN2_FL);
  setMotor(-1, globalSpeed, PWM_ML, IN1_ML, IN2_ML);
  setMotor(-1, globalSpeed, PWM_BL, IN1_BL, IN2_BL);
  setMotor(-1, globalSpeed, PWM_FR, IN1_FR, IN2_FR);
  setMotor(-1, globalSpeed, PWM_MR, IN1_MR, IN2_MR);
  setMotor(-1, globalSpeed, PWM_BR, IN1_BR, IN2_BR);
}

// Lệnh H(Dừng lại)
void stopMotor() {
  setMotor(0, 0, PWM_FL, IN1_FL, IN2_FL);
  setMotor(0, 0, PWM_ML, IN1_ML, IN2_ML);
  setMotor(0, 0, PWM_BL, IN1_BL, IN2_BL);
  setMotor(0, 0, PWM_FR, IN1_FR, IN2_FR);
  setMotor(0, 0, PWM_MR, IN1_MR, IN2_MR);
  setMotor(0, 0, PWM_BR, IN1_BR, IN2_BR);
}

// Lệnh R(Chéo góc 120 bên phải)
void diagonalRight() {
  setServoAngle(0, 120 + fl_ofst);
  setServoAngle(1, 120 + ml_ofst);
  setServoAngle(2, 120 + bl_ofst);
  setServoAngle(4, 120 + fr_ofst);
  setServoAngle(5, 120 + mr_ofst);
  setServoAngle(6, 120 + br_ofst);
}

// Lệnh F(Chéo góc 60 bên trái)
void diagonalLeft() {
  setServoAngle(0, 60 + fl_ofst);
  setServoAngle(1, 60 + ml_ofst);
  setServoAngle(2, 60 + bl_ofst);
  setServoAngle(4, 60 + fr_ofst);
  setServoAngle(5, 60 + mr_ofst);
  setServoAngle(6, 60 + br_ofst);
}

// Lệnh O
void bigRight() {
  setServoAngle(0, 110 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 70 + bl_ofst);
  setServoAngle(4, 110 + fr_ofst);
  setServoAngle(5, 90 + mr_ofst);
  setServoAngle(6, 70 + br_ofst);
}

// Lệnh L
void smallRight() {
  setServoAngle(0, 100 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 80 + bl_ofst);
  setServoAngle(4, 100 + fr_ofst);
  setServoAngle(5, 90 + mr_ofst);
  setServoAngle(6, 80 + br_ofst);
}

// Lệnh U
void bigLeft() {
  setServoAngle(0, 70 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 110 + bl_ofst);
  setServoAngle(4, 70 + fr_ofst);
  setServoAngle(5, 90 + mr_ofst);
  setServoAngle(6, 110 + br_ofst);
}

// Lệnh J
void smallLeft() {
  setServoAngle(0, 80 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 100 + bl_ofst);
  setServoAngle(4, 80 + fr_ofst);
  setServoAngle(5, 90 + mr_ofst);
  setServoAngle(6, 100 + br_ofst);
}

// Lệnh K(Dừng servo)
void center() {
  setServoAngle(0, 90 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 90 + bl_ofst);
  setServoAngle(4, 90 + fr_ofst);
  setServoAngle(5, 90 + mr_ofst);
  setServoAngle(6, 90 + br_ofst);
}

// Lệnh E(Quay tròn về bên phải)
void rotateright() {
  setServoAngle(0, 160 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 20 + bl_ofst);
  setServoAngle(4, 20 + fr_ofst);
  setServoAngle(5, 90 + mr_ofst);
  setServoAngle(6, 160 + br_ofst);

  delay(500);

  setMotor(1, globalSpeed, PWM_FL, IN1_FL, IN2_FL);
  setMotor(1, globalSpeed / 2, PWM_ML, IN1_ML, IN2_ML);
  setMotor(1, globalSpeed, PWM_BL, IN1_BL, IN2_BL);
  setMotor(-1, globalSpeed, PWM_FR, IN1_FR, IN2_FR);
  setMotor(-1, globalSpeed / 2, PWM_MR, IN1_MR, IN2_MR);
  setMotor(-1, globalSpeed, PWM_BR, IN1_BR, IN2_BR);
}

// Lệnh Q(Quay tròn về bên trái)
void rotateleft() {
  setServoAngle(0, 160 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 20 + bl_ofst);
  setServoAngle(4, 20 + fr_ofst);
  setServoAngle(5, 90 + mr_ofst);
  setServoAngle(6, 160 + br_ofst);

  delay(500);

  setMotor(-1, globalSpeed, PWM_FL, IN1_FL, IN2_FL);
  setMotor(-1, globalSpeed / 2, PWM_ML, IN1_ML, IN2_ML);
  setMotor(-1, globalSpeed, PWM_BL, IN1_BL, IN2_BL);
  setMotor(1, globalSpeed, PWM_FR, IN1_FR, IN2_FR);
  setMotor(1, globalSpeed / 2, PWM_MR, IN1_MR, IN2_MR);
  setMotor(1, globalSpeed, PWM_BR, IN1_BR, IN2_BR);
}

// Lệnh D(Xoay góc 180 đi sang phải)
void crabright() {
  setMotor(-1, globalSpeed, PWM_FL, IN1_FL, IN2_FL);
  setMotor(-1, globalSpeed, PWM_ML, IN1_ML, IN2_ML);
  setMotor(-1, globalSpeed, PWM_BL, IN1_BL, IN2_BL);
  setMotor(-1, globalSpeed, PWM_FR, IN1_FR, IN2_FR);
  setMotor(-1, globalSpeed, PWM_MR, IN1_MR, IN2_MR);
  setMotor(-1, globalSpeed, PWM_BR, IN1_BR, IN2_BR);

  delay(500);

  setServoAngle(0, 180 + fl_ofst);
  setServoAngle(1, 180 + ml_ofst);
  setServoAngle(2, 180 + bl_ofst);
  setServoAngle(4, 180 + fr_ofst);
  setServoAngle(5, 180 + mr_ofst);
  setServoAngle(6, 180 + br_ofst);
}

// Lệnh A - Now handled in processCommand for servo, keep motor function
void crableft() {
  setMotor(1, globalSpeed, PWM_FL, IN1_FL, IN2_FL);
  setMotor(1, globalSpeed, PWM_ML, IN1_ML, IN2_ML);
  setMotor(1, globalSpeed, PWM_BL, IN1_BL, IN2_BL);
  setMotor(1, globalSpeed, PWM_FR, IN1_FR, IN2_FR);
  setMotor(1, globalSpeed, PWM_MR, IN1_MR, IN2_MR);
  setMotor(1, globalSpeed, PWM_BR, IN1_BR, IN2_BR);

  delay(500);

  setServoAngle(0, 0 + fl_ofst);
  setServoAngle(1, 0 + ml_ofst);
  setServoAngle(2, 0 + bl_ofst);
  setServoAngle(4, 0 + fr_ofst);
  setServoAngle(5, 0 + mr_ofst);
  setServoAngle(6, 0 + br_ofst);
}

// Điều khiển động cơ DC
void setMotor(int dir, int pwmVal, int pwm, int in1, int in2) {
  analogWrite(pwm, pwmVal);
  if (dir == 1) {
    digitalWrite(in1, HIGH);
    digitalWrite(in2, LOW);
  } else if (dir == -1) {
    digitalWrite(in1, LOW);
    digitalWrite(in2, HIGH);
  } else {
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
  }
}

// Hàm điều khiển xung PWM cho servo
void setServoAngle(int channel, int angle) {
  angle = constrain(angle, 0, 180);
  int pulse = map(angle, 0, 180, SERVOMIN, SERVOMAX);
  pwm.setPWM(channel, 0, pulse);
}
