/*
 * Servo Diagnostic Tool for PCA9685
 * Upload this to test if PCA9685 and servos are working
 */

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Try default address 0x40
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

#define SERVOMIN  150  // PWM for 0 degrees
#define SERVOMAX  600  // PWM for 180 degrees

void setup() {
    Serial.begin(9600);
    delay(1000);

    Serial.println("====================================");
    Serial.println("   PCA9685 Servo Diagnostic Tool");
    Serial.println("====================================");

    // Scan I2C bus
    Serial.println("\n[1] Scanning I2C bus...");
    Wire.begin();

    int deviceCount = 0;
    for (byte address = 1; address < 127; address++) {
        Wire.beginTransmission(address);
        byte error = Wire.endTransmission();

        if (error == 0) {
            Serial.print("    Found device at 0x");
            if (address < 16) Serial.print("0");
            Serial.print(address, HEX);

            if (address == 0x40) {
                Serial.println(" <- PCA9685 (default)");
            } else if (address >= 0x40 && address <= 0x7F) {
                Serial.println(" <- Possible PCA9685");
            } else {
                Serial.println();
            }
            deviceCount++;
        }
    }

    if (deviceCount == 0) {
        Serial.println("    ERROR: No I2C devices found!");
        Serial.println("    Check wiring: SDA=Pin20, SCL=Pin21 on Mega");
        Serial.println("    Make sure PCA9685 VCC is connected to 5V");
    } else {
        Serial.print("    Total devices found: ");
        Serial.println(deviceCount);
    }

    // Initialize PCA9685
    Serial.println("\n[2] Initializing PCA9685...");
    pwm.begin();
    pwm.setPWMFreq(50);  // 50Hz for servos
    Serial.println("    PCA9685 initialized at 50Hz");

    // Test info
    Serial.println("\n[3] Servo PWM settings:");
    Serial.print("    SERVOMIN (0 deg):   ");
    Serial.println(SERVOMIN);
    Serial.print("    SERVOMAX (180 deg): ");
    Serial.println(SERVOMAX);
    Serial.print("    SERVOMID (90 deg):  ");
    Serial.println((SERVOMIN + SERVOMAX) / 2);

    Serial.println("\n====================================");
    Serial.println("Commands (type in Serial Monitor):");
    Serial.println("  0-5    : Select servo channel");
    Serial.println("  a      : All channels");
    Serial.println("  t      : Test sweep current channel");
    Serial.println("  m      : Move to middle (90 deg)");
    Serial.println("  l      : Move to low (0 deg)");
    Serial.println("  h      : Move to high (180 deg)");
    Serial.println("  r      : Raw PWM test (150-600)");
    Serial.println("  +/-    : Fine adjust +/- 10 PWM");
    Serial.println("====================================\n");

    // Initial test - move all to middle
    Serial.println("Moving all servos to 90 degrees...");
    for (int i = 0; i < 6; i++) {
        setServoAngle(i, 90);
        delay(100);
    }
    Serial.println("Done. If servos didn't move, check:");
    Serial.println("  1. External power to PCA9685 V+ terminal");
    Serial.println("  2. Servo signal wires connected correctly");
    Serial.println("  3. Servo power (red) and GND (brown) connected\n");
}

int currentChannel = 0;
int currentPWM = (SERVOMIN + SERVOMAX) / 2;
bool allChannels = false;

void loop() {
    if (Serial.available() > 0) {
        char c = Serial.read();

        switch (c) {
            case '0': case '1': case '2':
            case '3': case '4': case '5':
                currentChannel = c - '0';
                allChannels = false;
                Serial.print("Selected channel: ");
                Serial.println(currentChannel);
                break;

            case 'a':
            case 'A':
                allChannels = true;
                Serial.println("Selected: ALL channels");
                break;

            case 't':
            case 'T':
                testSweep();
                break;

            case 'm':
            case 'M':
                currentPWM = (SERVOMIN + SERVOMAX) / 2;
                applyPWM();
                Serial.println("Moved to MIDDLE (90 deg)");
                break;

            case 'l':
            case 'L':
                currentPWM = SERVOMIN;
                applyPWM();
                Serial.println("Moved to LOW (0 deg)");
                break;

            case 'h':
            case 'H':
                currentPWM = SERVOMAX;
                applyPWM();
                Serial.println("Moved to HIGH (180 deg)");
                break;

            case 'r':
            case 'R':
                rawPWMTest();
                break;

            case '+':
            case '=':
                currentPWM = min(currentPWM + 10, 700);
                applyPWM();
                Serial.print("PWM: ");
                Serial.println(currentPWM);
                break;

            case '-':
            case '_':
                currentPWM = max(currentPWM - 10, 100);
                applyPWM();
                Serial.print("PWM: ");
                Serial.println(currentPWM);
                break;
        }
    }
}

void applyPWM() {
    if (allChannels) {
        for (int i = 0; i < 6; i++) {
            pwm.setPWM(i, 0, currentPWM);
        }
        Serial.print("All channels -> PWM: ");
    } else {
        pwm.setPWM(currentChannel, 0, currentPWM);
        Serial.print("Channel ");
        Serial.print(currentChannel);
        Serial.print(" -> PWM: ");
    }
    Serial.println(currentPWM);
}

void setServoAngle(int channel, int angle) {
    angle = constrain(angle, 0, 180);
    int pulse = map(angle, 0, 180, SERVOMIN, SERVOMAX);
    pwm.setPWM(channel, 0, pulse);

    Serial.print("Ch");
    Serial.print(channel);
    Serial.print(": ");
    Serial.print(angle);
    Serial.print(" deg (PWM:");
    Serial.print(pulse);
    Serial.println(")");
}

void testSweep() {
    Serial.println("\n--- Sweep Test ---");
    Serial.println("0 -> 90 -> 180 -> 90 -> 0");

    // 0 degrees
    Serial.println("Moving to 0 degrees...");
    if (allChannels) {
        for (int i = 0; i < 6; i++) pwm.setPWM(i, 0, SERVOMIN);
    } else {
        pwm.setPWM(currentChannel, 0, SERVOMIN);
    }
    delay(1000);

    // 90 degrees
    Serial.println("Moving to 90 degrees...");
    int mid = (SERVOMIN + SERVOMAX) / 2;
    if (allChannels) {
        for (int i = 0; i < 6; i++) pwm.setPWM(i, 0, mid);
    } else {
        pwm.setPWM(currentChannel, 0, mid);
    }
    delay(1000);

    // 180 degrees
    Serial.println("Moving to 180 degrees...");
    if (allChannels) {
        for (int i = 0; i < 6; i++) pwm.setPWM(i, 0, SERVOMAX);
    } else {
        pwm.setPWM(currentChannel, 0, SERVOMAX);
    }
    delay(1000);

    // Back to 90
    Serial.println("Moving to 90 degrees...");
    if (allChannels) {
        for (int i = 0; i < 6; i++) pwm.setPWM(i, 0, mid);
    } else {
        pwm.setPWM(currentChannel, 0, mid);
    }
    delay(1000);

    // 0 degrees
    Serial.println("Moving to 0 degrees...");
    if (allChannels) {
        for (int i = 0; i < 6; i++) pwm.setPWM(i, 0, SERVOMIN);
    } else {
        pwm.setPWM(currentChannel, 0, SERVOMIN);
    }

    Serial.println("--- Sweep Complete ---\n");
}

void rawPWMTest() {
    Serial.println("\n--- Raw PWM Test ---");
    Serial.println("Testing PWM values: 100, 200, 300, 400, 500, 600");

    int testValues[] = {100, 200, 300, 400, 500, 600};

    for (int i = 0; i < 6; i++) {
        Serial.print("PWM: ");
        Serial.println(testValues[i]);

        if (allChannels) {
            for (int ch = 0; ch < 6; ch++) pwm.setPWM(ch, 0, testValues[i]);
        } else {
            pwm.setPWM(currentChannel, 0, testValues[i]);
        }
        delay(1000);
    }

    Serial.println("--- Raw Test Complete ---\n");
}
