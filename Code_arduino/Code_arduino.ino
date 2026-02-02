#include <Adafruit_PWMServoDriver.h>

// Động cơ phía trước bên trái
#define PWM_FL 13
#define IN2_FL 23
#define IN1_FL 22

// Động cơ giữa bên trái
#define PWM_ML 11
#define IN2_ML 29
#define IN1_ML 28

// Động cơ phía sau bên trái
#define PWM_BL 9
#define IN2_BL 51
#define IN1_BL 50

// Động cơ phía trước bên phải
#define PWM_FR 12
#define IN2_FR 24
#define IN1_FR 25

// Động cơ giữa bên phải
#define PWM_MR 10
#define IN2_MR 30
#define IN1_MR 31

// Động cơ phía sau bên phải
#define PWM_BR 8
#define IN2_BR 52
#define IN1_BR 53

// Sai số bù trừ servo
int fr_ofst = 0; 
int mr_ofst = 0;
int br_ofst = 0;
int fl_ofst = 0;
int ml_ofst = 0;
int bl_ofst = 0;

// Vị trí bắt đầu servo
int start_angle = 90;

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
  Serial.println("Setting servo to 90 degrees");
  setServoAngle(0, start_angle + fl_ofst);  // Kênh 0: FL
  setServoAngle(1, start_angle + ml_ofst);  // Kênh 1: ML
  setServoAngle(2, start_angle + bl_ofst);  // Kênh 2: BL
  setServoAngle(3, start_angle + fr_ofst);  // Kênh 3: FR
  setServoAngle(4, start_angle + mr_ofst);  // Kênh 4: MR
  setServoAngle(5, start_angle + br_ofst);  // Kênh 5: BR
}
  
void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read(); 

    // Xử lí các lệnh
    switch (cmd) {
      case 'W':
        forward();
        break;
      case 'S':
        reverse();
        break;
      case 'H':
        stopMotor();
        break;
      case 'L':
        smallRight();
        break;
      case 'J':
        smallLeft();
        break;
      case 'R':
        diagonalRight();
        break;
      case 'F':
        diagonalLeft();
        break;
      case 'K':
        center();
        break;
      case 'Q':
        rotateleft();
        break;
      case 'E':
        rotateright();
        break;
      case 'A':
        crableft();
        break;
      case 'D':
        crabright();
        break;
      case 'U':
        bigLeft();
        break;
      case 'O':
        bigRight();
        break;

      default:
        break;
    }
  }
}
// Lệnh W(Tiến lên)
void forward() {
  // Run the motor clockwise
  setMotor(1, 255, PWM_FL, IN1_FL, IN2_FL);
  setMotor(1, 255, PWM_ML, IN1_ML, IN2_ML);
  setMotor(1, 255, PWM_BL, IN1_BL, IN2_BL);
  setMotor(1, 255, PWM_FR, IN1_FR, IN2_FR);
  setMotor(1, 255, PWM_MR, IN1_MR, IN2_MR);
  setMotor(1, 255, PWM_BR, IN1_BR, IN2_BR);
}
// Lệnh S(Lùi xuống)
void reverse() {
  // Run the motor counter-clockwise
  setMotor(-1, 255, PWM_FL, IN1_FL, IN2_FL);
  setMotor(-1, 255, PWM_ML, IN1_ML, IN2_ML);
  setMotor(-1, 255, PWM_BL, IN1_BL, IN2_BL);
  setMotor(-1, 255, PWM_FR, IN1_FR, IN2_FR);
  setMotor(-1, 255, PWM_MR, IN1_MR, IN2_MR);
  setMotor(-1, 255, PWM_BR, IN1_BR, IN2_BR);
}
// Lệnh H(Dừng lại)
void stopMotor() {
  // Stop the motor
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
  setServoAngle(3, 120 + fr_ofst);
  setServoAngle(4, 120 + mr_ofst);
  setServoAngle(5, 120 + br_ofst);
}
// Lệnh F(Chéo góc 60 bên trái)
void diagonalLeft() {
  setServoAngle(0, 60 + fl_ofst);
  setServoAngle(1, 60 + ml_ofst);
  setServoAngle(2, 60 + bl_ofst);
  setServoAngle(3, 60 + fr_ofst);
  setServoAngle(4, 60 + mr_ofst);
  setServoAngle(5, 60 + br_ofst);
}
// Lệnh O
void bigRight() {
  setServoAngle(0, 110 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 70 + bl_ofst);
  setServoAngle(3, 110 + fr_ofst);
  setServoAngle(4, 90 + mr_ofst);
  setServoAngle(5, 70 + br_ofst);
}
// Lệnh L
void smallRight() {
  setServoAngle(0, 100 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 80 + bl_ofst);
  setServoAngle(3, 100 + fr_ofst);
  setServoAngle(4, 90 + mr_ofst);
  setServoAngle(5, 80 + br_ofst);
}
// Lệnh U
void bigLeft() {
  setServoAngle(0, 70 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 110 + bl_ofst);
  setServoAngle(3, 70 + fr_ofst);
  setServoAngle(4, 90 + mr_ofst);
  setServoAngle(5, 110 + br_ofst);
}
// Lệnh J
void smallLeft() {
  setServoAngle(0, 80 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 100 + bl_ofst);
  setServoAngle(3, 80 + fr_ofst);
  setServoAngle(4, 90 + mr_ofst);
  setServoAngle(5, 100 + br_ofst);
}
// Lệnh K(Dừng servo)
void center() {
  setServoAngle(0, 90 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 90 + bl_ofst);
  setServoAngle(3, 90 + fr_ofst);
  setServoAngle(4, 90 + mr_ofst);
  setServoAngle(5, 90 + br_ofst);
}
// Lệnh E(Quay tròn về bên phải)
void rotateright() {
  setServoAngle(0, 160 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 20 + bl_ofst);
  setServoAngle(3, 20 + fr_ofst);
  setServoAngle(4, 90 + mr_ofst);
  setServoAngle(5, 160 + br_ofst);
  
  delay(500);

  setMotor(1, 255, PWM_FL, IN1_FL, IN2_FL);
  setMotor(1, 127, PWM_ML, IN1_ML, IN2_ML);
  setMotor(1, 255, PWM_BL, IN1_BL, IN2_BL);
  setMotor(-1, 255, PWM_FR, IN1_FR, IN2_FR);
  setMotor(-1, 127, PWM_MR, IN1_MR, IN2_MR);
  setMotor(-1, 255, PWM_BR, IN1_BR, IN2_BR);
}
// Lệnh Q(Quay tròn về bên trái)
void rotateleft() {
  setServoAngle(0, 160 + fl_ofst);
  setServoAngle(1, 90 + ml_ofst);
  setServoAngle(2, 20 + bl_ofst);
  setServoAngle(3, 20 + fr_ofst);
  setServoAngle(4, 90 + mr_ofst);
  setServoAngle(5, 160 + br_ofst);
  
  delay(500);

  setMotor(-1, 255, PWM_FL, IN1_FL, IN2_FL);
  setMotor(-1, 127, PWM_ML, IN1_ML, IN2_ML);
  setMotor(-1, 255, PWM_BL, IN1_BL, IN2_BL);
  setMotor(1, 255, PWM_FR, IN1_FR, IN2_FR);
  setMotor(1, 127, PWM_MR, IN1_MR, IN2_MR);
  setMotor(1, 255, PWM_BR, IN1_BR, IN2_BR);
}
// Lệnh D(Xoay góc 180 đi sang phải)
void crabright() {
  setMotor(-1, 255, PWM_FL, IN1_FL, IN2_FL);
  setMotor(-1, 255, PWM_ML, IN1_ML, IN2_ML);
  setMotor(-1, 255, PWM_BL, IN1_BL, IN2_BL);
  setMotor(-1, 255, PWM_FR, IN1_FR, IN2_FR);
  setMotor(-1, 255, PWM_MR, IN1_MR, IN2_MR);
  setMotor(-1, 255, PWM_BR, IN1_BR, IN2_BR);

  delay(500);

  setServoAngle(0, 180 + fl_ofst);
  setServoAngle(1, 180 + ml_ofst);
  setServoAngle(2, 180 + bl_ofst);
  setServoAngle(3, 180 + fr_ofst);
  setServoAngle(4, 180 + mr_ofst);
  setServoAngle(5, 180 + br_ofst);

}
// Lệnh A(Xoay góc 0 đi sang trái)
void crableft() {
  setMotor(1, 255, PWM_FL, IN1_FL, IN2_FL);
  setMotor(1, 255, PWM_ML, IN1_ML, IN2_ML);
  setMotor(1, 255, PWM_BL, IN1_BL, IN2_BL);
  setMotor(1, 255, PWM_FR, IN1_FR, IN2_FR);
  setMotor(1, 255, PWM_MR, IN1_MR, IN2_MR);
  setMotor(1, 255, PWM_BR, IN1_BR, IN2_BR);
  
  delay(500);

  setServoAngle(0, 0 + fl_ofst);
  setServoAngle(1, 0 + ml_ofst);
  setServoAngle(2, 0 + bl_ofst);
  setServoAngle(3, 0 + fr_ofst);
  setServoAngle(4, 0 + mr_ofst);
  setServoAngle(5, 0 + br_ofst);

}
// Lệnh H(dừng động cơ)
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
  angle = constrain(angle, 0, 180); // Bảo vệ cực an toàn để tránh góc ngoài khoảng 0-180
  int pulse = map(angle, 0, 180, SERVOMIN, SERVOMAX);
  pwm.setPWM(channel, 0, pulse);
}