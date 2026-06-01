# Roverv2 — Robot Structure & Control Architecture

A 6-wheel Mars-rover-style mobile robot with **independent wheel steering** and a **rocker-bogie running gear**, providing omnidirectional movement (forward, reverse, crab, rotate-in-place, diagonal, and multi-radius turns).

---

## 1. Physical / Body Structure

### 1.1 Overall Layout

The rover uses a **6-wheel rocker-bogie chassis**, not a rigid rectangular frame. Each side carries three steer-drive wheel modules through an articulated rocker-bogie linkage, while the body is mounted above the suspension structure.

A **transverse shaft** runs across the chassis to couple the left and right suspension pivots. In the CAD, this cross-shaft normally carries a **bevel-gear set** (hidden in some views) to transfer articulation between the two sides and stabilize body attitude during terrain traversal.

Conceptually, the arrangement is:

```
                FRONT

        FL o                 o FR
            \               /
             \   rocker    /
        ML o--\-----------/--o MR
               \         /
                \_______/        ← body carried above articulated linkage
                /       \
        BL o---/         \---o BR

                 REAR
```

Key structural interpretation:
- **6 steer-drive wheels**: each wheel has its own steering servo and drive motor.
- **Passive terrain-compliance mechanism**: rocker-bogie linkage provides obstacle negotiation and keeps more wheels in contact with the ground.
- **Left-right mechanical coupling**: transverse shaft + bevel gears synchronize/articulate the two sides mechanically.
- **Body shell / electronics bay** sits above the running gear rather than acting as the primary load-bearing rigid axle frame.

### 1.2 Main Physical Dimensions

| Parameter | Value |
|----------|-------|
| Overall length | **490 mm** |
| Overall width (outer edge to outer edge of wheels) | **300 mm** |
| Body width | **200 mm** |
| Overall height (ground to highest point) | **280 mm** |
| Ground clearance | **100 mm** |
| Front overhang (nose beyond front wheel axis) | **50 mm** |
| Rear overhang (tail beyond rear wheel axis) | **95 mm** |
| Net mass (including electronics, battery, wiring) | **15 kg** |

### 1.3 Suspension / Articulation Structure

The mechanical platform is best described as a **rocker-bogie-derived articulated suspension**:

- **Rocker members** carry the outer wheel supports and transmit terrain-induced pitch motion to the chassis.
- **Bogie members** support the remaining wheel pair on each side and improve step-climbing / load sharing.
- **Central pivoting structure** allows relative angular motion between the left and right sides.
- **Cross-shaft coupling** links both sides mechanically; in the intended design this is implemented using a shaft through the chassis with a **bevel-gear set** mounted on it.

This means terrain compliance is achieved primarily by **mechanical articulation**, not merely by tire deformation.

### 1.4 Body / Enclosure

| Section | Purpose |
|---------|---------|
| **Top lid (red)** | Removable cover for internal access |
| **Main body (red + white side panels)** | Houses the Arduino Mega 2560, PCA9685 servo driver, and DC motor driver boards |
| **Raised front module** | Reserved for sensors / camera / Raspberry Pi |
| **Rear box** | Battery pack + MQTT-Serial bridge (Raspberry Pi) |

### 1.5 Wheel Module (× 6)

Each of the six wheel modules is an **independent steer-drive assembly** mounted onto the rocker-bogie suspension members.

```
        ┌─────────────┐
        │  SERVO      │   ← Vertical steering axis (yaw)
        │  (steering) │     rotates entire wheel assembly 0°–180°
        └──────┬──────┘
               │
        ┌──────┴──────┐
        │  BRACKET    │   ← Mounting structure to suspension arm
        └──────┬──────┘
               │
     ┌─────────┴─────────┐
     │  DC MOTOR         │   ← JGA25-370 geared, 130 rpm
     │  (drive)          │     with encoder, PWM speed
     └─────────┬─────────┘
               │
          ╔════╧════╗
          ║  TIRE   ║         ← Treaded rubber wheel
          ╚═════════╝
```

**Key characteristics:**
- **Steering**: one RC servo per wheel, mounted vertically; rotates the bracket around a vertical axis.
  - 90° = wheel points straight ahead
  - 0° / 180° = wheel turned 90° left / right (for crab)
  - Limited to 0–180° physical range
- **Drive**: one JGA25-370 DC gear motor per wheel, driven by an H-bridge board.
  - Direction controlled by two digital pins (IN1/IN2)
  - Speed controlled by PWM (0–255), min useful PWM ≈ 80
- Steering and drive are **fully decoupled** at each wheel.
- The wheel modules are **not mounted to a rigid axle beam**; they are carried by the articulated rocker-bogie members.

### 1.6 Wheel Naming Convention

| Code label | Position | Servo Ch (PCA9685) |
|-----------|----------|--------------------|
| `FL` | Front Left  | 0 |
| `ML` | Mid Left    | 1 |
| `BL` | Back Left   | 2 |
| `FR` | Front Right | 4 |
| `MR` | Mid Right   | 5 |
| `BR` | Back Right  | 6 |

> Channels 3 and 7 on the PCA9685 are intentionally unused.

---

## 2. Electronics & Wiring

### 2.1 System Block Diagram

```
┌─────────────────┐      MQTT over TLS (8883)      ┌─────────────────┐
│  Windows PC     │ ─────────────────────────────→ │  HiveMQ Cloud   │
│  Python Tkinter │      topic: car/control        │  MQTT Broker    │
│  (operator GUI) │                                └────────┬────────┘
└─────────────────┘                                         │ subscribe
                                                            │
                                                   ┌────────▼────────┐
                                                   │  Raspberry Pi   │
                                                   │  pi_mqtt_bridge │
                                                   │  (MQTT→Serial)  │
                                                   └────────┬────────┘
                                                            │ USB-Serial 9600 baud
                                                   ┌────────▼────────┐
                                                   │  Arduino Mega   │
                                                   │  2560           │
                                                   │  (firmware)     │
                                                   └──┬──────────────┘
                                                      │
                            ┌─────────────────────────┴─────────────────────────┐
                            │ I²C (SDA=20, SCL=21)          GPIO (PWM + IN1/IN2)│
                     ┌──────▼──────┐                  ┌──────▼──────┐
                     │  PCA9685    │                  │ 3× H-Bridge │
                     │  16-ch PWM  │                  │ Motor Drvrs │
                     └──────┬──────┘                  └──────┬──────┘
                            │                                │
                   ┌────────┴────────┐              ┌────────┴────────┐
                   │  6× Steering    │              │  6× DC Motors   │
                   │  Servos         │              │  (JGA25-370)    │
                   └─────────────────┘              └─────────────────┘
```

### 2.2 Arduino Pin Map (DC motors)

Three L298N H-bridge boards, one per axle. On each board: **Out1 (ENA) = left wheel, Out2 (ENB) = right wheel**.

| Label | PWM (EN) | IN1 | IN2 | Driver Board |
|-------|----------|-----|-----|--------------|
| FL | 12 | 24 | 25 | Front driver, Out 1 (ENA) |
| FR | 11 | 26 | 27 | Front driver, Out 2 (ENB) |
| ML | 10 | 28 | 29 | Middle driver, Out 1 (ENA) |
| MR |  9 | 30 | 31 | Middle driver, Out 2 (ENB) |
| BL |  8 | 50 | 51 | Rear driver, Out 1 (ENA) |
| BR |  7 | 52 | 53 | Rear driver, Out 2 (ENB) |

### 2.3 PCA9685 Servo Driver

- Interface: I²C on Arduino pins `SDA=20 / SCL=21`
- PWM frequency: 50 Hz
- Pulse range: `SERVOMIN=150` (0°) to `SERVOMAX=600` (180°)
- External 5–6 V supply wired to the PCA9685 V+ terminal (servos cannot be powered from the Arduino 5 V rail)

---

## 3. Control Architecture

### 3.1 Command Pipeline

```
User button / key
      │
      ▼
Python GUI  ──► MQTT publish "car/control"
                         │
                         ▼
              Raspberry Pi bridge
                         │ writes ASCII to /dev/ttyUSB0
                         ▼
              Arduino serial buffer
                         │ parsed on '\n' or '\r'
                         ▼
              ┌───────────────────────┐
              │ length == 1 ?         │
              │   yes → processSingle │
              │   no  → processCommand│
              └───────────────────────┘
```

The Arduino firmware buffers incoming bytes (max 15 chars) until a newline arrives, with a **500 ms stale-buffer timeout** to recover from dropped characters.

### 3.2 Command Protocol

#### A. Single-character motion presets

| Cmd | Action | Servo pattern | Motor pattern |
|-----|--------|---------------|----------------|
| `W` | Forward          | — (keep current) | All +speed |
| `S` | Reverse          | — | All −speed |
| `H` | Stop (emergency) | — | All 0 |
| `A` | Crab Left        | All wheels → 0°   | All +speed |
| `D` | Crab Right       | All wheels → 180° | All −speed |
| `Q` | Rotate Left      | Outer ±160°, mids 90°, inner ±20° | Opposite sides spin opposite |
| `E` | Rotate Right     | (same pattern)                    | (opposite of Q) |
| `K` | Center servos    | All → 90° | — |
| `F` | Diagonal Left    | All → 60°  | — |
| `R` | Diagonal Right   | All → 120° | — |
| `J` | Small Left turn  | FL/BL → 80°/100°, FR/BR → 80°/100° | — |
| `L` | Small Right turn | FL/BL → 100°/80°, FR/BR → 100°/80° | — |
| `U` | Big Left turn    | FL/BL → 70°/110°, FR/BR → 70°/110° | — |
| `O` | Big Right turn   | FL/BL → 110°/70°, FR/BR → 110°/70° | — |

> Middle wheels on rotate commands run at `globalSpeed / 2` because they sit near the body's rotation center — reduces tire scrub.

#### B. Multi-character commands (always terminated with `\n`)

| Syntax | Purpose | Example |
|--------|---------|---------|
| `CH:ANGLE\n`       | Set one servo   | `0:90\n` (FL → 90°) |
| `*:ANGLE\n`        | Set **all** servos | `*:60\n` |
| `MOTOR:DIR\n`      | Motor at global speed | `FL:1\n`, `MR:-1\n`, `BL:0\n` |
| `MOTOR:DIR:PWM\n`  | Motor with explicit speed | `FL:1:180\n` |
| `SPD:VALUE\n`      | Set `globalSpeed` (0–255) | `SPD:150\n` |
| `OFST:CH:VAL\n`    | Set servo calibration offset (−20 … +20) | `OFST:2:15\n` |

### 3.3 Firmware State

The Arduino firmware maintains a small amount of runtime state:

| Variable | Purpose | Default |
|----------|---------|---------|
| `globalSpeed` | PWM used by preset motor commands | `200` (~78 %) |
| `fl_ofst … br_ofst` | Per-servo calibration offset (degrees) | `0` |
| `start_angle` | Boot-up servo position | `90` (straight) |
| `inputBuffer` | Serial command buffer | `""` |
| `lastCharTime` | Stale-buffer watchdog | — |

Limits: `MOTOR_MIN_PWM = 80`, `MOTOR_MAX_PWM = 255`.

### 3.4 Servo Calibration

Each wheel's steering servo has a mechanical offset from ideal center. Calibration is stored in two places:

1. **`servo_calibration.json`** on the PC (persistent, loaded by `Motor_Test_UI.py`).
2. **Runtime offsets** inside the Arduino, pushed via `OFST:CH:VAL\n` at connect time.

Calibration flow in `Motor_Test_UI.py`:

```
[ 0° button ]  → send raw 0° to servo
[ -1 / +1  ]  → nudge physical angle until wheel is exactly straight
[ CAL      ]  → save current nudge as offset, persist to JSON, push OFST:
[ RST      ]  → clear offset to 0
```

Current saved offsets (`servo_calibration.json`):

| Channel | Offset |
|---------|--------|
| 0 (FL) | 0 |
| 1 (ML) | +1 |
| 2 (BL) | +15 |
| 4 (FR) | +15 |
| 5 (MR) | +4 |
| 6 (BR) | +3 |

### 3.5 Software Components

| File | Role |
|------|------|
| `Code_arduino/Code_arduino.ino` | Arduino firmware: serial parser, motor/servo control, motion presets |
| `Servo_Diagnostic/Servo_Diagnostic.ino` | Standalone PCA9685 channel sweep for bring-up |
| `pi_mqtt_bridge.py` | Raspberry Pi: subscribe to `car/control`, forward payload to USB serial |
| `Giao_dien_v2.py` | Main operator GUI (icon buttons, one-character commands) |
| `Motor_Test_UI.py` | Diagnostic GUI: per-servo sliders, per-motor FWD/REV/STOP, speed slider, servo calibration |
| `servo_calibration.json` | Persisted servo offsets |

---

## 4. Motion Summary

| Capability | How it is achieved |
|------------|--------------------|
| Forward / reverse | All servos at 90° (straight), all motors same direction |
| Crab (sideways) | All servos pivoted to 0° or 180°, all motors same direction |
| Rotate in place | Outer wheels angled inward (≈ ±160°/±20°), left & right sides driven opposite |
| Diagonal travel | All servos set to 60° or 120°, motors forward |
| Variable-radius turn | Front wheels and rear wheels angled symmetrically (70/80/100/110°), motors forward |
| Rough-terrain compliance | Passive rocker-bogie articulation + cross-shaft / bevel-gear coupling |
| Per-wheel test | `FL:1:150\n` style commands from `Motor_Test_UI.py` |

---

## 5. Coordinate & Naming Conventions

- **Front** = the end with the raised electronics module (see body render).
- **Left / Right** are defined from the robot's point of view, looking forward.
- **Servo angle increases** from the wheel pointing 90° left (0°) through straight-ahead (90°) to 90° right (180°).
- **Motor direction `+1`** = wheel surface moves rearward → robot moves forward.
- Offsets are **added** to the desired logical angle before the PWM is written, so the operator always commands "logical" degrees and the firmware compensates for assembly tolerance.
