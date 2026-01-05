# 6 Wheels - Hexapod Robot Control System

A sophisticated hexapod robot control system featuring omnidirectional movement capabilities. This project combines Arduino-based hardware control with a Python desktop GUI application, communicating via MQTT protocol for remote robot operation.

## Features

- **Omnidirectional Movement**: Move in any direction without rotating the robot body
- **13 Movement Commands**: Including forward/reverse, rotation, strafing, and diagonal movements
- **Independent Wheel Control**: 6 motors with individual servo-controlled wheel angles
- **Remote Control**: MQTT-based communication through HiveMQ cloud broker
- **User-Friendly GUI**: Tkinter-based desktop application with intuitive button interface
- **Real-Time Response**: Low-latency control for precise robot movements

## Hardware Requirements

### Electronics
- Arduino ATmega2560 microcontroller
- 6x DC motors (with encoders)
- 6x Servo motors (for wheel angle adjustment)
- PCA9685 16-Channel I2C PWM Driver
- Motor driver boards (for DC motor control)
- Power supply system

### Motor Configuration
- **Left Side**: Front-Left (FL), Mid-Left (ML), Back-Left (BL)
- **Right Side**: Front-Right (FR), Mid-Right (MR), Back-Right (BR)
- Each motor has encoder feedback and PWM speed control
- Each wheel has servo-controlled angle adjustment (0-180°)

## Software Requirements

### Desktop Application
- Python 3.7 or higher
- Required Python packages:
  - `tkinter` (GUI framework)
  - `paho-mqtt` (MQTT client)
  - `Pillow` (Image handling)
  - `typing_extensions` (required for Python 3.7)

### Arduino Firmware
- Arduino IDE
- Adafruit PWM Servo Driver Library

## Installation

### 1. Desktop GUI Setup

```bash
# Navigate to project directory
cd "C:\Users\SandMan\Desktop\DATNK26\6 wheels"

# Activate virtual environment (or hubtenv)
hubtenv\Scripts\activate

# Install dependencies
pip install paho-mqtt pillow typing_extensions
```

### 2. Arduino Setup

1. Open `Code_arduino/Code_arduino.ino` in Arduino IDE
2. Install required library: **Adafruit PWM Servo Driver Library**
   - Go to: Sketch > Include Library > Manage Libraries
   - Search for "Adafruit PWM Servo Driver"
   - Install the library
3. Connect your Arduino ATmega2560 board
4. Upload the sketch to the board

## Usage

### Starting the Control Application

```bash
# Activate virtual environment
hubtenv\Scripts\activate

# Run the GUI application
python Giao_dien_v2.py
```

### Control Commands

The GUI provides 13 command buttons for robot control:

| Button | Command | Function |
|--------|---------|----------|
| **Q** | Rotate Left | Spin counterclockwise in place |
| **W** | Forward | Move forward (all wheels aligned) |
| **E** | Rotate Right | Spin clockwise in place |
| **R** | Diagonal Right | Move diagonally right (wheels at 120°) |
| **A** | Crab Left | Strafe left (wheels at 0°) |
| **S** | Reverse | Move backward (all wheels aligned) |
| **D** | Crab Right | Strafe right (wheels at 180°) |
| **F** | Diagonal Left | Move diagonally left (wheels at 60°) |
| **U** | Big Left Turn | Large radius left turn |
| **J** | Small Left Turn | Small radius left turn |
| **K** | Center Servo | Reset all wheels to 90° center position |
| **L** | Small Right Turn | Small radius right turn |
| **O** | Big Right Turn | Large radius right turn |
| **H/Stop** | Emergency Stop | Stop all motors immediately |

## Project Structure

```
6 wheels/
├── Code_arduino/
│   └── Code_arduino.ino          # Arduino firmware for motor/servo control
├── Giao_dien_v2.py              # Desktop GUI control application
├── icons/                        # Button icon graphics
│   ├── q.png, w.png, e.png, r.png
│   ├── a.png, s.png, d.png, f.png
│   ├── u.png, j.png, k.png, l.png, o.png
│   ├── stop.png
│   └── Keyboard Layout.png      # Reference guide
├── hubtenv/                      # Python virtual environment
└── README.md                     # This file
```

## Technical Details

### Communication Architecture

```
Desktop GUI (Python/Tkinter)
    ↓ MQTT over TLS/SSL (Port 8883)
HiveMQ Cloud Broker
    ↓ Serial/WiFi Connection
Arduino ATmega2560
    ↓ PWM/I2C Signals
Motors & Servos
```

### MQTT Configuration
- **Broker**: `80d38917ab9144ccb7ecee5f086e00f9.s1.eu.hivemq.cloud`
- **Port**: 8883 (TLS/SSL encrypted)
- **Topic**: `car/control`
- **Authentication**: Username and password required

### Motor Control Details

**DC Motors (Speed Control)**
- PWM-based speed control (0-255)
- Direction control via H-bridge (IN1, IN2 pins)
- Encoder feedback for odometry

**Servo Motors (Angle Control)**
- Controlled via PCA9685 I2C PWM driver
- Range: 0-180 degrees
- Allows independent wheel angle adjustment for omnidirectional movement

### Pin Assignments (Arduino)

**Motor PWM Pins:**
- FL: Pin 13, ML: Pin 11, BL: Pin 9
- FR: Pin 12, MR: Pin 10, BR: Pin 8

**Direction Control Pins:**
- Each motor has IN1 and IN2 pins for direction control

**Encoder Pins:**
- Each motor has ENCA and ENCB pins for feedback

**I2C for Servo Control:**
- SDA: Pin 20, SCL: Pin 21
- PCA9685 channels 0-5 for servo motors

## Movement Capabilities

This hexapod robot features **holonomic drive**, enabling:
- Movement in any direction without body rotation
- Simultaneous translation and rotation
- Crab-walking (sideways movement)
- Diagonal movements
- Variable-radius turning
- Precise positioning control

## Troubleshooting

### GUI Won't Connect to MQTT
- Check internet connection
- Verify MQTT broker credentials
- Ensure firewall allows port 8883

### Arduino Not Responding
- Verify serial connection
- Check power supply to motors
- Ensure PCA9685 I2C connection is correct
- Check all motor and servo wiring

### Motors Running Erratically
- Calibrate servo positions
- Check encoder connections
- Verify power supply voltage and current capacity

## Development Notes

- Project developed as part of DATNK26 (likely a capstone/thesis project)
- Code comments and variable names include Vietnamese
- GUI application: `Giao_dien_v2.py` ("Interface v2" in Vietnamese)

## License

This project is provided as-is for educational and research purposes.

## Credits

Developed as part of DATNK26 program, 2025.
