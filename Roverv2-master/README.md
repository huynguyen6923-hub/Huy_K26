# 6 Wheels - Hexapod Robot Control System

A sophisticated hexapod robot control system featuring omnidirectional movement capabilities. This project combines Arduino-based hardware control with a Python desktop GUI application, communicating via MQTT protocol for remote robot operation.

## Features

- **Omnidirectional Movement**: Move in any direction without rotating the robot body
- **13 Movement Commands**: Including forward/reverse, rotation, strafing, and diagonal movements
- **Independent Wheel Control**: 6 motors with individual servo-controlled wheel angles
- **Remote Control**: MQTT-based communication through HiveMQ cloud broker
- **Three Control GUIs**:
  - `Giao_dien_v2.py` — original icon-button interface
  - `Giao_dien_v3.py` — racing-dashboard themed UI with steering wheel, speedometer,
    speed-mode pills, **live webcam panel**, and editable Pi-host settings
  - `Motor_Test_UI.py` — per-motor / per-servo diagnostics + servo calibration
- **Live Webcam Streaming**: USB webcam on the Pi → MJPEG over LAN → displayed inside
  the v3 GUI (`pi_camera_stream.py`)
- **Real-Time Response**: Low-latency control for precise robot movements

## Hardware Requirements

### Electronics
- Arduino ATmega2560 microcontroller
- Raspberry Pi (MQTT to Serial bridge)
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

### Desktop Application (Windows PC)
- Python 3.7 or higher
- Required Python packages:
  - `tkinter` (GUI framework — built-in)
  - `paho-mqtt` (MQTT client)
  - `Pillow` (image decoding for the webcam panel)

### Raspberry Pi (services)
- Raspberry Pi OS (64-bit, **Lite** recommended — no desktop required)
- Python 3 (preinstalled)
- Required packages (all available via apt, no pip needed):
  - `python3-paho-mqtt` — MQTT client for the bridge
  - `python3-serial`   — USB-serial for the bridge
  - `python3-opencv`   — webcam capture & JPEG encoding for the camera stream

### Arduino Firmware
- Arduino IDE
- Adafruit PWM Servo Driver Library

## Project Structure

```
Roverv2/
├── Code_arduino/
│   └── Code_arduino.ino          # Main Arduino firmware (motors + servos)
├── Servo_Diagnostic/
│   └── Servo_Diagnostic.ino      # Standalone PCA9685 channel sweep
├── Giao_dien_v2.py               # Original icon-button GUI (Vietnamese)
├── Giao_dien_v3.py               # Racing-dashboard GUI w/ live webcam panel
├── Motor_Test_UI.py              # Per-motor / per-servo test + calibration UI
├── pi_mqtt_bridge.py             # Pi: MQTT(car/control) → /dev/ttyUSB0
├── pi_camera_stream.py           # Pi: webcam → MJPEG + raw/face/hands modes
├── systemd/
│   ├── rover-bridge.service      # systemd unit: auto-start MQTT bridge
│   └── rover-camera.service      # systemd unit: auto-start camera streamer
├── servo_calibration.json        # Persisted per-channel servo offsets
├── rover_settings.json           # PC-side settings (Pi host IP, etc.)
├── icons/                        # Button icon graphics
├── pictures/                     # Screenshots
├── ROBOT_STRUCTURE.md            # Full mechanical + electrical spec
└── README.md                     # This file
```

## System Architecture

```
                              ┌─────────────────┐
                              │  Windows PC     │
                              │  Giao_dien_v3   │◀───────── MJPEG (HTTP)
                              │  (Tkinter GUI)  │            ▲
                              └────────┬────────┘            │
                                       │ MQTT publish        │
                                       │ topic: car/control  │
                                       ▼                     │
                              ┌─────────────────┐            │
                              │  HiveMQ Cloud   │            │
                              │  TLS port 8883  │            │
                              └────────┬────────┘            │
                                       │ subscribe           │
                                       ▼                     │
                              ┌─────────────────────┐        │
                              │   Raspberry Pi 4    │        │
                              │  ┌───────────────┐  │        │
                              │  │ pi_mqtt_      │  │        │
                              │  │   bridge.py   │  │        │
                              │  └──────┬────────┘  │        │
                              │  ┌──────┴────────┐  │        │
                              │  │ pi_camera_    │──┼────────┘
                              │  │   stream.py   │  │  :8080/stream
                              │  └──────┬────────┘  │
                              └─────────┼───────────┘
                                        │ USB Serial 9600
                                        ▼
                              ┌─────────────────┐
                              │  Arduino Mega   │
                              │     2560        │
                              └────────┬────────┘
                                       │ PWM / I²C
                              ┌────────┴────────┐
                              │                 │
                        ┌─────▼─────┐     ┌─────▼─────┐
                        │ 6× DC     │     │ 6× Servos │
                        │ Motors    │     │ (PCA9685) │
                        └───────────┘     └───────────┘
```

## Installation

### 1. Windows PC Setup

```bash
# Navigate to project directory
cd E:\Robotic\Rover-Project\v2\Roverv2

# Create virtual environment
python -m venv mqtt_env_win

# Activate virtual environment
mqtt_env_win\Scripts\activate

# Install dependencies
pip install paho-mqtt pillow
```

### 2. Raspberry Pi Setup

Use the **Raspberry Pi Imager** to flash *Raspberry Pi OS Lite (64-bit)*. In the
Imager's "OS customization" panel, set hostname, username/password, WiFi, and
**enable SSH** — this avoids ever needing a screen + keyboard on the Pi.

After the Pi boots, SSH in and install everything in one shot:

```bash
sudo apt update
sudo apt install -y python3-paho-mqtt python3-serial python3-opencv

# sanity check
python3 -c "import paho.mqtt.client, serial, cv2; print('all ok')"

# verify hardware is detected
ls /dev/video*                          # USB webcam → /dev/video0
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null   # Arduino → /dev/ttyUSB0 (or ACM0)
```

Copy both Pi-side scripts from your PC:

```powershell
# from PowerShell on the Windows PC
scp pi_mqtt_bridge.py    aios@<pi-ip>:~/
scp pi_camera_stream.py  aios@<pi-ip>:~/
```

Run them in two SSH sessions (manual, useful while developing):

```bash
# Session 1 — MQTT bridge (forwards car/control → Arduino)
python3 pi_mqtt_bridge.py
# add --port /dev/ttyACM0 if Arduino enumerated as ACM

# Session 2 — webcam MJPEG streamer
python3 pi_camera_stream.py
# defaults to 640x480 @ 15 fps on port 8080
```

Browser test: open `http://<pi-ip>:8080/` from any device on the LAN —
you should see the live camera feed.

#### Auto-start on boot via systemd (recommended for demo / production)

Two unit files live in `systemd/`. Push them once and enable:

```powershell
# from PC
scp systemd/rover-bridge.service systemd/rover-camera.service aios@<pi-ip>:~/
```

```bash
# on Pi
sudo mv ~/rover-bridge.service ~/rover-camera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo usermod -a -G dialout aios          # one-time: serial port access
sudo systemctl enable --now rover-bridge.service
sudo systemctl enable --now rover-camera.service
sudo reboot                               # so dialout group takes effect
```

Verify after reboot:

```bash
systemctl status rover-bridge --no-pager
systemctl status rover-camera --no-pager   # both should be "active (running)"
journalctl -u rover-bridge -f              # live MQTT command log
```

The camera service starts in **`raw` mode** by default. To run a vision mode
manually for a demo, stop the service first so the same port/camera is free:

```bash
sudo systemctl stop rover-camera
python3 pi_camera_stream.py --mode face       # Haar face follower
# or for hands (see "Hand-pose control" below)
```

To make a vision mode the *default* boot behaviour, override the unit:

```bash
sudo systemctl edit rover-camera
# in the editor that opens, paste:
#   [Service]
#   ExecStart=
#   ExecStart=/usr/bin/python3 /home/aios/pi_camera_stream.py --mode face
sudo systemctl restart rover-camera
```

> **WARNING — never let Windows "format" or "repair" the Pi's SD card.**
> Pi cards have an ext4 partition Windows can't read; clicking "format" wipes
> the OS. If Windows pops up that dialog when you insert the card, click
> **Cancel**. Use a Linux box or an SD card reader app (e.g. Pi Imager itself)
> if you need to inspect the card.

### 3. Arduino Setup

1. Open `Code_arduino/Code_arduino.ino` in Arduino IDE
2. Install required library: **Adafruit PWM Servo Driver Library**
   - Go to: Sketch > Include Library > Manage Libraries
   - Search for "Adafruit PWM Servo Driver"
   - Install the library
3. Connect your Arduino ATmega2560 board
4. Upload the sketch to the board

## Vision Modes (`pi_camera_stream.py --mode ...`)

The camera streamer can layer simple vision processing on top of the live
feed and publish servo commands directly to MQTT. **Forward motion is never
auto-commanded** — vision modes only steer; you drive forward / reverse with
W / S in the GUI. A misdetection therefore can't run the rover away.

| Mode | Detector | Steers via | Extra deps |
|------|----------|------------|------------|
| `raw` (default) | none | — | — |
| `face` | OpenCV Haar cascade | discrete `J` / `K` / `L` (small left / centre / small right) | `opencv-data` for the XML cascade |
| `hands` | MediaPipe Hands | continuous per-channel servo angle (`0:90`, `4:88`, …) with EMA smoothing | `mediapipe` (Python ≤ 3.12 only) |

Common flags:

```text
--mode {raw,face,hands}
--no-mqtt                 visualize only; do not publish commands
--width / --height / --fps   camera capture size
--deadzone 0.16           face mode: centre deadzone (frac of frame width)
--ema 0.4                 hand mode: smoothing alpha (lower = silkier)
--max-steer 60            hand mode: clip steering magnitude (degrees)
```

### Face-follow mode

```bash
sudo apt install -y opencv-data        # one-time, provides the Haar XML
sudo systemctl stop rover-camera
python3 pi_camera_stream.py --mode face --no-mqtt   # warm-up, no commands
python3 pi_camera_stream.py --mode face             # live, steers the rover
```

The CAMERA panel shows: green rectangle on biggest face, yellow deadzone
lines, white centre crosshair, and live status (`CENTERED (K)`,
`TURN LEFT (J)`, `TURN RIGHT (L)`, `NO FACE`).

### Hand-pose mode

MediaPipe doesn't currently ship wheels for Python 3.13 (the default on
Pi OS Trixie). We use [`uv`](https://github.com/astral-sh/uv) to drop
Python 3.11 into a sandboxed venv just for this script.

```bash
# one-time setup on Pi
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv venv --python 3.11 ~/.venv-hands
uv pip install --python ~/.venv-hands/bin/python mediapipe opencv-python paho-mqtt
~/.venv-hands/bin/python -c "import mediapipe, cv2, paho.mqtt.client; print('ok')"
```

Run the stream in hand mode (the camera service must be stopped first):

```bash
sudo systemctl stop rover-camera
~/.venv-hands/bin/python ~/pi_camera_stream.py --mode hands --no-mqtt
# when happy, drop --no-mqtt to actually steer the rover
~/.venv-hands/bin/python ~/pi_camera_stream.py --mode hands
```

Control mapping:

| You do | Robot does |
|--------|------------|
| Hold hand straight up in front of camera | Wheels centred (90°) |
| Tilt hand left | Wheels steer left |
| Tilt hand right | Wheels steer right |
| Remove hand from view (~1 s) | Wheels recentre |
| Hold **W** in v3 GUI | Drive forward at the current wheel angle |
| Hold **S** in v3 GUI | Drive reverse |
| Release W/S | Stop driving (wheels keep last hand angle) |
| **Space / Esc** in v3 GUI | Emergency stop |

> **While hand mode is active, do not also drag the steering slider in the
> v3 GUI.** Both publish per-channel servo commands to the same topic and
> would fight each other. The W/S/Stop buttons are fine — they only command
> motors, not servos.

To make hand mode the boot default, point the camera service's
`ExecStart` at the venv Python:

```bash
sudo systemctl edit rover-camera
# paste:
#   [Service]
#   ExecStart=
#   ExecStart=/home/aios/.venv-hands/bin/python /home/aios/pi_camera_stream.py --mode hands
sudo systemctl restart rover-camera
```

## Usage

### Racing-dashboard GUI (recommended) — `Giao_dien_v3.py`

```bash
mqtt_env_win\Scripts\activate
python Giao_dien_v3.py
```

Panels (top to bottom):
- **CAMERA** — live video from the Pi. The Pi host IP is editable in this
  panel; press `↻` (or Enter) to reconnect after a change. The current value
  is persisted to `rover_settings.json`. Toggle "Stream ON" to disable
  streaming when not needed.
- **STEERING** — drag the wide bar (or use ←/→ keys) to set wheel angle.
  Mode selector at top: ACKERMANN (front + rear opposite) or CRAB (all wheels
  parallel).
- **THROTTLE** — speedometer + four speed-mode pills (CRAWL / SLOW / CRUISE /
  TURBO). Press 1-4 to switch.
- **DRIVE** — hold-to-drive FORWARD (W) / REVERSE (S) buttons. STOP on
  Space/Esc.

### Original GUI — `Giao_dien_v2.py`

```bash
python Giao_dien_v2.py
```

### Motor & Servo Test Application

```bash
# Per-motor / per-servo manual test + servo calibration
python Motor_Test_UI.py
```

### Camera-only test (no Tkinter)

Open `http://<pi-ip>:8080/` in any browser to view the raw stream — useful
when debugging the camera independently of the main GUI.

## Command Protocol

### Single Character Commands (DC Motors & Preset Servo Positions)

| Command | Function |
|---------|----------|
| `W` | Forward - all motors forward |
| `S` | Reverse - all motors backward |
| `H` | Stop - emergency stop all motors |
| `A` | Crab Left - strafe left |
| `D` | Crab Right - strafe right |
| `Q` | Rotate Left - spin counterclockwise |
| `E` | Rotate Right - spin clockwise |
| `R` | Diagonal Right - servos to 120° |
| `F` | Diagonal Left - servos to 60° |
| `K` | Center - all servos to 90° |
| `U` | Big Left Turn |
| `J` | Small Left Turn |
| `L` | Small Right Turn |
| `O` | Big Right Turn |

### Multi-Character Commands (Individual Servo Control)

| Command | Function |
|---------|----------|
| `0:90\n` | Set Servo channel 0 to 90° |
| `1:45\n` | Set Servo channel 1 to 45° |
| `2:180\n` | Set Servo channel 2 to 180° |
| `*:90\n` | Set ALL servos to 90° |

### Multi-Character Commands (Individual DC Motor Control)

| Command | Function |
|---------|----------|
| `FL:1\n` | FL motor forward |
| `FL:-1\n` | FL motor reverse |
| `FL:0\n` | FL motor stop |
| `ML:1\n` | ML motor forward |
| `MR:1\n` | MR motor forward |
| `BL:1\n` | BL motor forward |
| `BR:1\n` | BR motor forward |
| `FR:1\n` | FR motor forward |

**Motors:** FL (Front Left), ML (Mid Left), BL (Back Left), FR (Front Right), MR (Mid Right), BR (Back Right)

**Note:** All multi-character commands require newline (`\n`) terminator.

### Servo Channel Mapping (PCA9685)

| Channel | Wheel Position | Description |
|---------|----------------|-------------|
| 0 | FL | Front Left (Block 1) |
| 1 | ML | Mid Left (Block 1) |
| 2 | BL | Back Left (Block 1) |
| 3 | — | Unused |
| 4 | FR | Front Right (Block 2) |
| 5 | MR | Mid Right (Block 2) |
| 6 | BR | Back Right (Block 2) |

**Example Commands:**
- `0:90\n` → Set FL (Front Left) servo to 90°
- `4:45\n` → Set FR (Front Right) servo to 45°
- `*:90\n` → Set ALL servos to 90°

## MQTT Configuration

- **Broker**: `80d38917ab9144ccb7ecee5f086e00f9.s1.eu.hivemq.cloud`
- **Port**: 8883 (TLS/SSL encrypted)
- **Topic**: `car/control`
- **Username**: `datn2025`
- **Password**: `Datn2025`

## Pin Assignments (Arduino Mega 2560)

### DC Motor Pin Definitions (in code)

Three L298N H-bridge boards, one per axle. On each board: **Out1 (ENA) = left motor, Out2 (ENB) = right motor**. Code labels match the physical motor.

| Label | PWM Pin | IN1 Pin | IN2 Pin | L298 Board |
|-------|---------|---------|---------|------------|
| FL | 12 | 24 | 25 | Front (Out1, ENA) |
| FR | 11 | 26 | 27 | Front (Out2, ENB) |
| ML | 10 | 28 | 29 | Middle (Out1, ENA) |
| MR |  9 | 30 | 31 | Middle (Out2, ENB) |
| BL |  8 | 50 | 51 | Back (Out1, ENA) |
| BR |  7 | 52 | 53 | Back (Out2, ENB) |

### I2C for PCA9685 Servo Driver
- **SDA**: Pin 20
- **SCL**: Pin 21
- **Servo channels in use**: 0/1/2 (left side: FL/ML/BL), 4/5/6 (right side: FR/MR/BR). Channels 3 and 7 are intentionally unused.
    
## Troubleshooting

### Servos Not Working
1. Check PCA9685 I2C connection (SDA=Pin20, SCL=Pin21)
2. Verify external power supply connected to PCA9685 V+ terminal
3. Use `Servo_Diagnostic.ino` to test I2C and individual channels
4. Check servo wiring (Signal, VCC, GND)

### Only One Servo Works / Wrong Servo Moves
- Servo channel mapping may not match physical wiring
- Use `Motor_Test_UI.py` to test each channel (0-5) individually
- Note which physical servo moves for each channel
- Re-wire or update code to match

### MQTT Connection Issues
- Check internet connection on both PC and Pi
- Verify MQTT credentials
- Ensure firewall allows port 8883
- Check Pi bridge is running: `ps -ef | grep pi_mqtt_bridge`

### Commands Not Received by Arduino
- Check Pi-to-Arduino USB/Serial connection
- If Arduino enumerated as `/dev/ttyACM0`, run `python3 pi_mqtt_bridge.py --port /dev/ttyACM0`
- If `Permission denied: /dev/ttyUSB0` on Pi, add user to dialout group:
  `sudo usermod -a -G dialout $USER && sudo reboot`
- Open Arduino Serial Monitor (9600 baud) to see received commands
- Multi-char commands need newline terminator (`\n`)

### Buffer Issues (Commands Stop Working)
- Arduino has 500ms timeout to clear stale buffer
- Ensure commands are properly terminated
- Press `H` (Stop) to reset state

### Webcam Stream Issues (`Giao_dien_v3.py` CAMERA panel)
- "Offline: ..." in the status line → Pi unreachable. Check the IP in the
  CAMERA panel matches `hostname -I` on the Pi.
- Browser test independently: `http://<pi-ip>:8080/`
- Stream slow or laggy → drop resolution:
  `python3 pi_camera_stream.py --width 320 --height 240 --fps 10`
- Wrong webcam selected → `python3 pi_camera_stream.py --device 1`
- `OSError: [Errno 98] Address already in use` → another `pi_camera_stream.py`
  is already running. Stop the service or kill the manual one:
  `sudo systemctl stop rover-camera` and / or `pkill -f pi_camera_stream.py`.

### Vision Mode Issues
- Face mode fails with `module 'cv2' has no attribute 'data'` →
  `sudo apt install -y opencv-data`
- Hand mode fails with `ERROR: No matching distribution found for mediapipe`
  → Python 3.13 has no MediaPipe wheel. Install Python 3.11 in a venv via
  `uv` (see "Hand-pose mode" above) and run with `~/.venv-hands/bin/python`.
- Hand-mode wheels twitch → increase smoothing: `--ema 0.25` (default 0.4).
- Hand-mode steering feels too laggy → `--ema 0.6` for snappier response.
- Hand-mode steering insufficient → `--max-steer 90` (default 60).

## Development Notes

- Project developed as part of DATNK26 (capstone/thesis project)
- Code comments include Vietnamese
- `Giao_dien_v2.py` = "Interface v2" in Vietnamese
- `Motor_Test_UI.py` added for debugging servo/motor issues
- `Giao_dien_v3.py` adds a racing-dashboard look-and-feel and integrates the
  live MJPEG webcam feed coming from `pi_camera_stream.py`
- `pi_camera_stream.py` uses **only stdlib `http.server` + `cv2`** (no Flask
  dependency) so it doubles as a quick "is OpenCV installed on the Pi?" smoke
  test — if `import cv2` fails, OpenCV is missing.

## Files Description

| File | Description |
|------|-------------|
| `Giao_dien_v2.py` | Original control GUI with icon buttons |
| `Giao_dien_v3.py` | Racing-dashboard GUI: steering wheel canvas, speedometer, speed-mode pills, **live webcam panel**, MQTT log |
| `Motor_Test_UI.py` | Test GUI for individual servo (0-5) and DC motor (FL/ML/BL/FR/MR/BR) control + servo calibration save/load |
| `pi_mqtt_bridge.py` | Pi service: MQTT(`car/control`) → USB serial passthrough to Arduino |
| `pi_camera_stream.py` | Pi service: USB webcam → MJPEG over HTTP on `:8080/stream`, with `--mode raw` (default), `--mode face` (Haar cascade follower), `--mode hands` (MediaPipe hand-pose steering) |
| `systemd/rover-bridge.service`, `systemd/rover-camera.service` | systemd unit files for auto-starting both Pi services on boot |
| `servo_calibration.json` | Per-channel servo offsets (loaded by `Motor_Test_UI.py`, by `Giao_dien_v3.py`, and by `pi_camera_stream.py` hand mode if scp'd to the Pi) |
| `rover_settings.json` | PC-side settings persisted by `Giao_dien_v3.py` (currently: `pi_host`) |
| `Code_arduino.ino` | Main Arduino firmware with all commands |
| `Servo_Diagnostic.ino` | PCA9685 I²C diagnostic tool (standalone sketch) |
| `ROBOT_STRUCTURE.md` | Full mechanical + electrical specification (chassis, dimensions, pin map, command protocol details) |

## License

This project is provided as-is for educational and research purposes.

## Credits

Developed as part of DATNK26 program, 2025.
