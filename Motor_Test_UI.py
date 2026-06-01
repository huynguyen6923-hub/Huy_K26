import tkinter as tk
from tkinter import messagebox
import paho.mqtt.client as mqtt
import json
import os

# MQTT Configuration
BROKER = "80d38917ab9144ccb7ecee5f086e00f9.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "datn2025"
PASSWORD = "Datn2025"
TOPIC = "car/control"

class MotorTestUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Servo & Motor Test")
        self.root.configure(bg="#1e1e1e")

        # MQTT Client
        self.client = mqtt.Client()
        self.client.username_pw_set(USERNAME, PASSWORD)
        self.client.tls_set()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.connected = False

        self.status_var = tk.StringVar(value="Disconnected")
        self.servo_vars = {}
        self.servo_labels = {}
        self.speed_var = tk.IntVar(value=200)  # Global DC motor speed (0-255)

        # Servo calibration offsets
        self.servo_channels = [0, 1, 2, 4, 5, 6]
        self.servo_offsets = {ch: 0 for ch in self.servo_channels}
        self.calib_temp = {ch: 0 for ch in self.servo_channels}  # Temp angle during calibration
        self.offset_labels = {}
        self.calib_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "servo_calibration.json")
        self.load_calibration()

        self.create_widgets()
        self.connect_mqtt()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.status_var.set("Connected")
            self.status_label.configure(fg="#00ff00")
            self.send_all_offsets()

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.status_var.set("Disconnected")
        self.status_label.configure(fg="red")

    def connect_mqtt(self):
        try:
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_start()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def send_command(self, cmd):
        if self.connected:
            self.client.publish(TOPIC, cmd, qos=0)
            self.log(f">> {cmd.strip()}")
        else:
            self.log(f"[OFFLINE] {cmd.strip()}")

    def log(self, msg):
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)

    def set_servo(self, channel, angle):
        """Send servo command with calibration offset applied"""
        physical = angle + self.servo_offsets[channel]
        physical = max(0, min(180, physical))
        cmd = f"{channel}:{physical}\n"
        self.send_command(cmd)
        self.servo_labels[channel].config(text=f"{angle}°")

    def set_all_servos(self, angle):
        """Set all servos to same angle (with offsets)"""
        for ch in self.servo_channels:
            self.servo_vars[ch].set(angle)
            self.servo_labels[ch].config(text=f"{angle}°")
            physical = angle + self.servo_offsets[ch]
            physical = max(0, min(180, physical))
            self.send_command(f"{ch}:{physical}\n")

    # ========== CALIBRATION METHODS ==========

    def load_calibration(self):
        """Load servo offsets from file"""
        if os.path.exists(self.calib_file):
            try:
                with open(self.calib_file, 'r') as f:
                    data = json.load(f)
                for ch in self.servo_channels:
                    self.servo_offsets[ch] = data.get(str(ch), 0)
            except Exception:
                pass

    def save_calibration(self):
        """Save servo offsets to file"""
        data = {str(ch): self.servo_offsets[ch] for ch in self.servo_channels}
        with open(self.calib_file, 'w') as f:
            json.dump(data, f, indent=2)

    def send_all_offsets(self):
        """Send all calibration offsets to Arduino"""
        for ch in self.servo_channels:
            if self.servo_offsets[ch] != 0:
                self.send_command(f"OFST:{ch}:{self.servo_offsets[ch]}\n")

    def calib_nudge(self, channel, delta):
        """Nudge servo by delta degrees during calibration"""
        self.calib_temp[channel] += delta
        self.calib_temp[channel] = max(-45, min(45, self.calib_temp[channel]))
        # Move servo to physical position (0 + nudge amount)
        physical = self.calib_temp[channel]
        physical = max(0, min(180, physical))
        self.send_command(f"{channel}:{physical}\n")
        self.offset_labels[channel].config(text=f"({self.calib_temp[channel]:+d})")
        self.log(f"Calib CH{channel}: nudge to {physical}°")

    def calib_set(self, channel):
        """Set current nudge position as calibration offset"""
        self.servo_offsets[channel] = self.calib_temp[channel]
        self.save_calibration()
        self.send_command(f"OFST:{channel}:{self.servo_offsets[channel]}\n")
        self.offset_labels[channel].config(text=f"[{self.servo_offsets[channel]:+d}]", fg="#00ff00")
        self.log(f"CAL CH{channel}: offset = {self.servo_offsets[channel]}°")
        # Move servo to logical 0 with offset applied
        self.servo_vars[channel].set(0)
        self.set_servo(channel, 0)

    def calib_reset(self, channel):
        """Reset calibration offset to 0"""
        self.servo_offsets[channel] = 0
        self.calib_temp[channel] = 0
        self.save_calibration()
        self.send_command(f"OFST:{channel}:0\n")
        self.offset_labels[channel].config(text="(0)", fg="#888")
        self.log(f"RST CH{channel}: offset cleared")
        # Move servo to physical 0
        self.servo_vars[channel].set(0)
        self.send_command(f"{channel}:0\n")

    def calib_start(self, channel):
        """Start calibration: move servo to 0° (no offset) for alignment"""
        self.calib_temp[channel] = 0
        self.send_command(f"{channel}:0\n")
        self.offset_labels[channel].config(text="(0)", fg="#ffaa00")
        self.log(f"Calib CH{channel}: moved to 0° - use +/- to align")

    def update_servo_from_slider(self, channel, value):
        """Called when slider moves"""
        angle = int(float(value))
        self.servo_labels[channel].config(text=f"{angle}°")

    def send_servo_from_slider(self, channel):
        """Send current slider value"""
        angle = self.servo_vars[channel].get()
        self.set_servo(channel, angle)

    def on_speed_change(self, value):
        """Called when speed slider moves"""
        spd = int(float(value))
        self.speed_label.config(text=str(spd))

    def set_speed(self, speed):
        """Set global speed and send to Arduino"""
        self.speed_var.set(speed)
        self.speed_label.config(text=str(speed))
        self.send_command(f"SPD:{speed}\n")

    def send_motor_cmd(self, motor, direction):
        """Send individual motor command with current speed"""
        spd = self.speed_var.get()
        self.send_command(f"{motor}:{direction}:{spd}\n")

    def send_preset(self, cmd):
        """Send global speed then preset movement command"""
        spd = self.speed_var.get()
        self.send_command(f"SPD:{spd}\n")
        self.send_command(f"{cmd}\n")

    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg="#1e1e1e")
        header.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(header, text="MQTT:", bg="#1e1e1e", fg="white").pack(side=tk.LEFT)
        self.status_label = tk.Label(header, textvariable=self.status_var, bg="#1e1e1e", fg="red")
        self.status_label.pack(side=tk.LEFT, padx=5)

        # ========== SERVO SECTION ==========
        servo_frame = tk.LabelFrame(self.root, text="SERVO TEST (6 Channels)",
                                     bg="#1e1e1e", fg="#ffff00", font=("Arial", 14, "bold"))
        servo_frame.pack(padx=10, pady=5, fill=tk.X)

        # Servo layout: 2 rows (Left side, Right side)
        # Left: FL(5), ML(3), BL(2) | Right: FR(0), MR(4), BR(1)
        servo_layout = [
            ("LEFT (Block 1)", [(0, "FL"), (1, "ML"), (2, "BL")]),
            ("RIGHT (Block 2)", [(4, "FR"), (5, "MR"), (6, "BR")])
        ]

        for side_name, servos in servo_layout:
            # Side label row
            side_frame = tk.Frame(servo_frame, bg="#1e1e1e")
            side_frame.pack(fill=tk.X, padx=5, pady=5)
            tk.Label(side_frame, text=f"── {side_name} SIDE ──", bg="#1e1e1e",
                     fg="#ffaa00", font=("Arial", 11, "bold")).pack(anchor="w")

            for ch, name in servos:
                row_frame = tk.Frame(servo_frame, bg="#2b2b2b")
                row_frame.pack(fill=tk.X, padx=5, pady=3)

                # Channel label with name
                tk.Label(row_frame, text=f"{ch}: {name}", bg="#2b2b2b", fg="white",
                         font=("Arial", 11, "bold"), width=10, anchor="w").pack(side=tk.LEFT, padx=5)

                # Angle display
                self.servo_labels[ch] = tk.Label(row_frame, text="90°", bg="#2b2b2b", fg="#00ffff",
                                                  font=("Arial", 11, "bold"), width=5)
                self.servo_labels[ch].pack(side=tk.LEFT, padx=5)

                # Slider
                self.servo_vars[ch] = tk.IntVar(value=90)
                slider = tk.Scale(row_frame, from_=0, to=180, orient=tk.HORIZONTAL,
                                 variable=self.servo_vars[ch], length=200,
                                 bg="#2b2b2b", fg="white", highlightthickness=0,
                                 troughcolor="#444", activebackground="#00aaff",
                                 command=lambda v, c=ch: self.update_servo_from_slider(c, v))
                slider.pack(side=tk.LEFT, padx=5)

                # Send button
                tk.Button(row_frame, text="SET", command=lambda c=ch: self.send_servo_from_slider(c),
                          bg="#1565c0", fg="white", width=5, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

                # Quick angle buttons
                for angle in [0, 45, 90, 135, 180]:
                    tk.Button(row_frame, text=str(angle),
                             command=lambda c=ch, a=angle: [self.servo_vars[c].set(a), self.set_servo(c, a)],
                             bg="#333", fg="white", width=3).pack(side=tk.LEFT, padx=1)

                # Separator
                tk.Label(row_frame, text="|", bg="#2b2b2b", fg="#555").pack(side=tk.LEFT, padx=3)

                # Calibration offset display
                ofst = self.servo_offsets[ch]
                ofst_text = f"[{ofst:+d}]" if ofst != 0 else "(0)"
                ofst_color = "#00ff00" if ofst != 0 else "#888"
                self.offset_labels[ch] = tk.Label(row_frame, text=ofst_text, bg="#2b2b2b",
                                                   fg=ofst_color, font=("Arial", 9, "bold"), width=5)
                self.offset_labels[ch].pack(side=tk.LEFT)

                # Go to 0° for calibration
                tk.Button(row_frame, text="0°",
                         command=lambda c=ch: self.calib_start(c),
                         bg="#555", fg="white", width=2, font=("Arial", 9)).pack(side=tk.LEFT, padx=1)

                # Nudge -1° / +1°
                tk.Button(row_frame, text="-1",
                         command=lambda c=ch: self.calib_nudge(c, -1),
                         bg="#444", fg="white", width=2, font=("Arial", 9)).pack(side=tk.LEFT, padx=1)
                tk.Button(row_frame, text="+1",
                         command=lambda c=ch: self.calib_nudge(c, 1),
                         bg="#444", fg="white", width=2, font=("Arial", 9)).pack(side=tk.LEFT, padx=1)

                # Calibrate button
                tk.Button(row_frame, text="CAL",
                         command=lambda c=ch: self.calib_set(c),
                         bg="#f57f17", fg="black", width=3, font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)

                # Reset button
                tk.Button(row_frame, text="RST",
                         command=lambda c=ch: self.calib_reset(c),
                         bg="#616161", fg="white", width=3, font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)

        # All servos control
        all_frame = tk.Frame(servo_frame, bg="#1e1e1e")
        all_frame.pack(fill=tk.X, padx=5, pady=10)

        tk.Label(all_frame, text="ALL SERVOS:", bg="#1e1e1e", fg="white",
                 font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=5)

        for angle in [0, 45, 90, 135, 180]:
            tk.Button(all_frame, text=f"All {angle}°",
                     command=lambda a=angle: self.set_all_servos(a),
                     bg="#7b1fa2", fg="white", width=7, font=("Arial", 10)).pack(side=tk.LEFT, padx=3)

        # ========== INDIVIDUAL DC MOTOR TEST ==========
        dc_frame = tk.LabelFrame(self.root, text="DC MOTOR TEST - JGA25-370 130rpm",
                                  bg="#1e1e1e", fg="#00ffff", font=("Arial", 14, "bold"))
        dc_frame.pack(padx=10, pady=5, fill=tk.X)

        # Speed control
        speed_frame = tk.Frame(dc_frame, bg="#1e1e1e")
        speed_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(speed_frame, text="SPEED:", bg="#1e1e1e", fg="white",
                 font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=5)

        self.speed_label = tk.Label(speed_frame, text="200", bg="#1e1e1e", fg="#00ffff",
                                     font=("Arial", 11, "bold"), width=4)
        self.speed_label.pack(side=tk.LEFT)

        speed_slider = tk.Scale(speed_frame, from_=0, to=255, orient=tk.HORIZONTAL,
                                variable=self.speed_var, length=250,
                                bg="#1e1e1e", fg="white", highlightthickness=0,
                                troughcolor="#444", activebackground="#00aaff",
                                command=self.on_speed_change)
        speed_slider.pack(side=tk.LEFT, padx=5)

        # Quick speed buttons
        for spd, label in [(80, "MIN"), (130, "50%"), (200, "78%"), (255, "MAX")]:
            tk.Button(speed_frame, text=label,
                     command=lambda s=spd: self.set_speed(s),
                     bg="#333", fg="white", width=4, font=("Arial", 9)).pack(side=tk.LEFT, padx=2)

        # DC motor layout: Left side, Right side
        dc_layout = [
            ("LEFT", ["FL", "ML", "BL"]),
            ("RIGHT", ["FR", "MR", "BR"])
        ]

        for side_name, motors in dc_layout:
            side_frame = tk.Frame(dc_frame, bg="#1e1e1e")
            side_frame.pack(fill=tk.X, padx=5, pady=5)
            tk.Label(side_frame, text=f"── {side_name} SIDE ──", bg="#1e1e1e",
                     fg="#ffaa00", font=("Arial", 11, "bold")).pack(anchor="w")

            for motor in motors:
                row_frame = tk.Frame(dc_frame, bg="#2b2b2b")
                row_frame.pack(fill=tk.X, padx=5, pady=3)

                # Motor label
                tk.Label(row_frame, text=motor, bg="#2b2b2b", fg="white",
                         font=("Arial", 11, "bold"), width=5, anchor="w").pack(side=tk.LEFT, padx=5)

                # Forward button (sends with speed)
                tk.Button(row_frame, text="FWD",
                          command=lambda m=motor: self.send_motor_cmd(m, 1),
                          bg="#2e7d32", fg="white", width=5, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=3)

                # Stop button
                tk.Button(row_frame, text="STOP",
                          command=lambda m=motor: self.send_command(f"{m}:0\n"),
                          bg="#c62828", fg="white", width=5, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=3)

                # Reverse button (sends with speed)
                tk.Button(row_frame, text="REV",
                          command=lambda m=motor: self.send_motor_cmd(m, -1),
                          bg="#e65100", fg="white", width=5, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=3)

        # ========== ALL MOTORS CONTROL ==========
        motor_frame = tk.LabelFrame(self.root, text="ALL MOTORS",
                                     bg="#1e1e1e", fg="#00ffff", font=("Arial", 14, "bold"))
        motor_frame.pack(padx=10, pady=5, fill=tk.X)

        motor_inner = tk.Frame(motor_frame, bg="#1e1e1e")
        motor_inner.pack(pady=10)

        # Motor buttons in grid layout (send speed first, then command)
        tk.Button(motor_inner, text="W\nFORWARD", command=lambda: self.send_preset("W"),
                  bg="#2e7d32", fg="white", width=10, height=2, font=("Arial", 10, "bold")).grid(row=0, column=1, padx=3, pady=3)

        tk.Button(motor_inner, text="Q\nROT L", command=lambda: self.send_preset("Q"),
                  bg="#6a1b9a", fg="white", width=10, height=2, font=("Arial", 10, "bold")).grid(row=0, column=0, padx=3, pady=3)

        tk.Button(motor_inner, text="E\nROT R", command=lambda: self.send_preset("E"),
                  bg="#6a1b9a", fg="white", width=10, height=2, font=("Arial", 10, "bold")).grid(row=0, column=2, padx=3, pady=3)

        tk.Button(motor_inner, text="A\nLEFT", command=lambda: self.send_preset("A"),
                  bg="#1565c0", fg="white", width=10, height=2, font=("Arial", 10, "bold")).grid(row=1, column=0, padx=3, pady=3)

        tk.Button(motor_inner, text="H\nSTOP", command=lambda: self.send_command("H\n"),
                  bg="#c62828", fg="white", width=10, height=2, font=("Arial", 12, "bold")).grid(row=1, column=1, padx=3, pady=3)

        tk.Button(motor_inner, text="D\nRIGHT", command=lambda: self.send_preset("D"),
                  bg="#1565c0", fg="white", width=10, height=2, font=("Arial", 10, "bold")).grid(row=1, column=2, padx=3, pady=3)

        tk.Button(motor_inner, text="S\nREVERSE", command=lambda: self.send_preset("S"),
                  bg="#e65100", fg="white", width=10, height=2, font=("Arial", 10, "bold")).grid(row=2, column=1, padx=3, pady=3)

        # ========== LOG ==========
        log_frame = tk.LabelFrame(self.root, text="Log", bg="#1e1e1e", fg="white")
        log_frame.pack(padx=10, pady=5, fill=tk.X)

        self.log_text = tk.Text(log_frame, height=4, bg="#0a0a0a", fg="#00ff00",
                                font=("Consolas", 9), width=60)
        self.log_text.pack(padx=5, pady=5)

        # ========== EMERGENCY STOP ==========
        tk.Button(self.root, text="EMERGENCY STOP", command=lambda: self.send_command("H\n"),
                  bg="#b71c1c", fg="white", font=("Arial", 16, "bold"),
                  width=20, height=2).pack(pady=10)

    def on_closing(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MotorTestUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
