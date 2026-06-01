import io
import json
import math
import os
import re
import socket
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from tkinter import messagebox, ttk

import paho.mqtt.client as mqtt
from PIL import Image, ImageTk

BROKER = "80d38917ab9144ccb7ecee5f086e00f9.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "datn2025"
PASSWORD = "Datn2025"
TOPIC = "car/control"

SERVO_CHANNELS = [0, 1, 2, 4, 5, 6]
STEER_THROTTLE_MS = 60

DEFAULT_PI_HOST = "192.168.2.249"
PI_STREAM_PORT = 8080
CAMERA_DISPLAY_W = 320
CAMERA_DISPLAY_H = 240
CAMERA_RECONNECT_DELAY = 3.0

SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "rover_settings.json"
)


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(d):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass

SPEED_MODES = [
    ("CRAWL",  100, "#3fb950"),
    ("SLOW",   150, "#00d9ff"),
    ("CRUISE", 200, "#d29922"),
    ("TURBO",  255, "#f85149"),
]

# ---- Racing dashboard palette ----
BG       = "#0a0e14"
PANEL    = "#11161d"
PANEL_HI = "#181f29"
ROW      = "#1c232e"
BORDER   = "#2a3340"
TEXT     = "#e6edf3"
TEXT_DIM = "#7d8590"
ACCENT   = "#00d9ff"
ACCENT_2 = "#ff6b35"
GOOD     = "#3fb950"
WARN     = "#d29922"
BAD      = "#f85149"


# ============================================================
# Custom canvas widgets
# ============================================================

class SteeringWheel(tk.Canvas):
    """Three-spoke racing steering wheel that rotates with steer_pos."""
    SIZE = 240

    def __init__(self, parent):
        super().__init__(parent, width=self.SIZE, height=self.SIZE,
                         bg=PANEL, highlightthickness=0)
        self.steer = 0

    def set_steer(self, value):
        self.steer = int(value)
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self.SIZE
        cx = cy = s // 2
        R_TICK_OUT = 110
        R_TICK_IN = 102
        R_RIM_OUT = 96
        R_RIM_IN = 76
        R_HUB = 26

        # Outer tick marks (fixed background)
        for tick in range(-90, 91, 15):
            ta = math.radians(tick)
            x1 = cx + math.sin(ta) * R_TICK_IN
            y1 = cy - math.cos(ta) * R_TICK_IN
            x2 = cx + math.sin(ta) * R_TICK_OUT
            y2 = cy - math.cos(ta) * R_TICK_OUT
            if tick == 0:
                color, w = ACCENT, 3
            elif tick % 45 == 0:
                color, w = TEXT_DIM, 2
            else:
                color, w = BORDER, 1
            self.create_line(x1, y1, x2, y2, fill=color, width=w)

        # Outer rim (fake depth: shadow ring + main rim + inner rim)
        self.create_oval(cx - R_RIM_OUT - 2, cy - R_RIM_OUT - 2,
                         cx + R_RIM_OUT + 2, cy + R_RIM_OUT + 2,
                         outline="#000000", width=1)
        self.create_oval(cx - R_RIM_OUT, cy - R_RIM_OUT,
                         cx + R_RIM_OUT, cy + R_RIM_OUT,
                         fill="#1c232e", outline="#3a4350", width=2)
        self.create_oval(cx - R_RIM_IN, cy - R_RIM_IN,
                         cx + R_RIM_IN, cy + R_RIM_IN,
                         fill=PANEL, outline=BORDER, width=2)

        # Three spokes (rotate with steer)
        a = math.radians(self.steer)
        spoke_angle_color = self._angle_color()
        for base in (0, 120, 240):
            ang = math.radians(base + self.steer)
            sx = cx + math.sin(ang) * (R_RIM_IN + 2)
            sy = cy - math.cos(ang) * (R_RIM_IN + 2)
            # shadow then highlight for "depth"
            self.create_line(cx, cy, sx, sy, fill="#0a0e14",
                             width=14, capstyle=tk.ROUND)
            self.create_line(cx, cy, sx, sy, fill="#3a4350",
                             width=10, capstyle=tk.ROUND)
            self.create_line(cx, cy, sx, sy, fill="#4a5460",
                             width=4, capstyle=tk.ROUND)

        # Top indicator notch (the "12 o'clock marker" on the rim)
        sin_a, cos_a = math.sin(a), math.cos(a)
        nx = cx + sin_a * (R_RIM_OUT - 8)
        ny = cy - cos_a * (R_RIM_OUT - 8)
        self.create_oval(nx - 10, ny - 10, nx + 10, ny + 10,
                         fill=spoke_angle_color, outline="")
        self.create_oval(nx - 5, ny - 5, nx + 5, ny + 5,
                         fill="#ffffff", outline="")

        # Central hub
        self.create_oval(cx - R_HUB - 2, cy - R_HUB - 2,
                         cx + R_HUB + 2, cy + R_HUB + 2,
                         fill="#000", outline="")
        self.create_oval(cx - R_HUB, cy - R_HUB,
                         cx + R_HUB, cy + R_HUB,
                         fill=PANEL_HI, outline=spoke_angle_color, width=2)

        # Center degree text
        if self.steer == 0:
            txt, color = "0°", TEXT_DIM
        else:
            txt = f"{self.steer:+d}°"
            color = TEXT
        self.create_text(cx, cy, text=txt, fill=color,
                         font=("Consolas", 13, "bold"))

    def _angle_color(self):
        a = abs(self.steer)
        if a < 20:
            return ACCENT
        if a < 60:
            return WARN
        return ACCENT_2


class SteeringBar(tk.Canvas):
    """Wide horizontal canvas slider that feels like a racing-pad axis."""
    HEIGHT = 64

    def __init__(self, parent, width=580, on_change=None, on_release=None):
        super().__init__(parent, width=width, height=self.HEIGHT,
                         bg=PANEL, highlightthickness=0, cursor="sb_h_double_arrow")
        self.w = width
        self.value = 0
        self.on_change = on_change
        self.on_release = on_release
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release_evt)
        self._draw()

    MARGIN = 36

    def set_value(self, v):
        self.value = max(-90, min(90, int(v)))
        self._draw()

    def _x_to_value(self, x):
        usable = self.w - 2 * self.MARGIN
        frac = (x - self.MARGIN) / max(1, usable)
        frac = max(0.0, min(1.0, frac))
        return int(round(-90 + frac * 180))

    def _value_to_x(self, v):
        usable = self.w - 2 * self.MARGIN
        frac = (v + 90) / 180
        return self.MARGIN + frac * usable

    def _on_press(self, ev):
        self.value = self._x_to_value(ev.x)
        self._draw()
        if self.on_change:
            self.on_change(self.value)

    def _on_drag(self, ev):
        self.value = self._x_to_value(ev.x)
        self._draw()
        if self.on_change:
            self.on_change(self.value)

    def _on_release_evt(self, _ev):
        if self.on_release:
            self.on_release()

    def _draw(self):
        self.delete("all")
        cy = self.HEIGHT // 2
        track_y0 = cy - 7
        track_y1 = cy + 7

        # Track background
        self.create_rectangle(self.MARGIN, track_y0, self.w - self.MARGIN, track_y1,
                              fill=BG, outline=BORDER, width=1)

        # Tick marks (every 30°)
        for tv in range(-90, 91, 30):
            tx = self._value_to_x(tv)
            if tv == 0:
                self.create_line(tx, cy - 16, tx, cy + 16, fill=TEXT_DIM, width=2)
            else:
                self.create_line(tx, cy - 11, tx, cy + 11, fill=BORDER, width=1)

        # Filled portion from center to current value
        cx = self._value_to_x(0)
        tx = self._value_to_x(self.value)
        if self.value != 0:
            color = self._color_for_value()
            x0, x1 = sorted([cx, tx])
            self.create_rectangle(x0, track_y0, x1, track_y1,
                                  fill=color, outline="")

        # Thumb (knob)
        col = self._color_for_value()
        self.create_oval(tx - 17, cy - 17, tx + 17, cy + 17,
                         fill="#000", outline="")
        self.create_oval(tx - 15, cy - 15, tx + 15, cy + 15,
                         fill=col, outline="#ffffff", width=2)
        self.create_oval(tx - 5, cy - 5, tx + 5, cy + 5,
                         fill="#ffffff", outline="")

        # End arrows
        self.create_text(16, cy, text="◀", fill=TEXT_DIM,
                         font=("Arial", 18, "bold"))
        self.create_text(self.w - 16, cy, text="▶", fill=TEXT_DIM,
                         font=("Arial", 18, "bold"))

    def _color_for_value(self):
        a = abs(self.value)
        if a == 0:
            return ACCENT
        if a < 30:
            return ACCENT
        if a < 60:
            return WARN
        return ACCENT_2


class Speedometer(tk.Canvas):
    """Semi-circular gauge showing PWM 0..255."""
    W, H = 220, 150

    def __init__(self, parent):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=PANEL, highlightthickness=0)
        self.value = 200
        self.label = ""

    def set_value(self, v, label=""):
        self.value = max(0, min(255, int(v)))
        self.label = label
        self._draw()

    def _draw(self):
        self.delete("all")
        cx, cy = self.W // 2, self.H - 20
        R = 90
        # Background semicircle (180° → 0° going CCW in tk = top half)
        self.create_arc(cx - R, cy - R, cx + R, cy + R,
                        start=180, extent=-180,
                        outline=BORDER, width=10, style=tk.ARC)

        # Color zones (the four speed modes light up the band they cover)
        zones = [(0, 100, GOOD), (100, 150, ACCENT),
                 (150, 200, WARN), (200, 255, BAD)]
        for lo, hi, col in zones:
            start = 180 - (lo / 255) * 180
            ext = -((hi - lo) / 255) * 180
            self.create_arc(cx - R + 6, cy - R + 6, cx + R - 6, cy + R - 6,
                            start=start, extent=ext,
                            outline=col, width=4, style=tk.ARC)

        # Tick marks
        for spd in range(0, 256, 32):
            frac = spd / 255
            ang = math.radians(180 - frac * 180)
            x1 = cx + math.cos(ang) * (R + 10)
            y1 = cy - math.sin(ang) * (R + 10)
            x2 = cx + math.cos(ang) * (R + 18)
            y2 = cy - math.sin(ang) * (R + 18)
            self.create_line(x1, y1, x2, y2, fill=TEXT_DIM, width=2)

        # Needle
        frac = self.value / 255
        ang = math.radians(180 - frac * 180)
        nx = cx + math.cos(ang) * (R - 12)
        ny = cy - math.sin(ang) * (R - 12)
        self.create_line(cx, cy, nx, ny, fill=ACCENT_2,
                         width=4, capstyle=tk.ROUND)
        self.create_oval(cx - 11, cy - 11, cx + 11, cy + 11,
                         fill=ACCENT_2, outline="")
        self.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                         fill="#ffffff", outline="")

        # Digital readout
        self.create_text(cx, cy - 30, text=str(self.value),
                         fill=TEXT, font=("Consolas", 22, "bold"))
        if self.label:
            self.create_text(cx, cy - 8, text=self.label,
                             fill=ACCENT, font=("Arial", 9, "bold"))


class StateLED(tk.Canvas):
    """Glowing LED-style state indicator."""
    SIZE = 84

    def __init__(self, parent):
        super().__init__(parent, width=self.SIZE, height=self.SIZE,
                         bg=PANEL, highlightthickness=0)
        self.color = "#3a4148"
        self._draw()

    def set_color(self, color):
        self.color = color
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self.SIZE
        cx = cy = s // 2
        # Outer dim ring (suggests glow)
        self.create_oval(cx - 38, cy - 38, cx + 38, cy + 38,
                         outline=self._dim(self.color, 0.25), width=2)
        self.create_oval(cx - 32, cy - 32, cx + 32, cy + 32,
                         outline=self._dim(self.color, 0.5), width=2)
        # LED body
        self.create_oval(cx - 26, cy - 26, cx + 26, cy + 26,
                         fill=self.color, outline="#444c56", width=2)
        # Highlight
        self.create_oval(cx - 18, cy - 22, cx - 4, cy - 8,
                         fill=self._lighten(self.color), outline="")

    @staticmethod
    def _dim(hex_color, factor):
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return "#222"
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

    @staticmethod
    def _lighten(hex_color):
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return "#fff"
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r = min(255, r + 80); g = min(255, g + 80); b = min(255, b + 80)
        return f"#{r:02x}{g:02x}{b:02x}"


# ============================================================
# Camera stream (MJPEG client)
# ============================================================

class CameraStream:
    """Background MJPEG client. Decodes frames in a worker thread and
    posts them to the Tk main thread via .after()."""

    _CL_RE = re.compile(rb"Content-Length:\s*(\d+)\s*\r\n\r\n")

    def __init__(self, label, on_status):
        self.label = label
        self.on_status = on_status
        self.url = ""
        self.running = False
        self.thread = None
        self._stop_event = threading.Event()
        self._frame_count = 0
        self._fps_t0 = time.time()

    def configure_url(self, url):
        self.url = url

    def start(self):
        if self.running:
            return
        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self._stop_event.set()

    def restart(self):
        self.stop()
        if self.thread is not None:
            self.thread.join(timeout=2.0)
        self.start()

    def _run(self):
        while self.running:
            self._post_status("Connecting...", ok=False)
            try:
                req = urllib.request.Request(self.url)
                with urllib.request.urlopen(req, timeout=3) as r:
                    self._post_status("LIVE", ok=True)
                    self._read_stream(r)
            except (urllib.error.URLError, OSError, socket.timeout) as e:
                msg = str(e)
                if len(msg) > 36:
                    msg = msg[:33] + "..."
                self._post_status(f"Offline: {msg}", ok=False)
            except Exception as e:
                self._post_status(f"Error: {e}", ok=False)
            if self._stop_event.wait(CAMERA_RECONNECT_DELAY):
                return

    def _read_stream(self, r):
        buf = b""
        while self.running:
            m = self._CL_RE.search(buf)
            if not m:
                chunk = r.read(4096)
                if not chunk:
                    return
                buf += chunk
                continue
            length = int(m.group(1))
            start = m.end()
            end = start + length
            while len(buf) < end and self.running:
                chunk = r.read(end - len(buf))
                if not chunk:
                    return
                buf += chunk
            if len(buf) < end:
                return
            jpeg = buf[start:end]
            buf = buf[end:]
            self._on_jpeg(jpeg)

    def _on_jpeg(self, jpeg_bytes):
        try:
            img = Image.open(io.BytesIO(jpeg_bytes))
            img.load()
            img = img.resize(
                (CAMERA_DISPLAY_W, CAMERA_DISPLAY_H), Image.NEAREST
            )
        except Exception:
            return
        self._frame_count += 1
        now = time.time()
        if now - self._fps_t0 >= 1.0:
            fps = self._frame_count / (now - self._fps_t0)
            self._frame_count = 0
            self._fps_t0 = now
            self._post_status(f"LIVE  •  {fps:.1f} fps", ok=True)
        try:
            self.label.after(0, self._apply_image, img)
        except RuntimeError:
            pass

    def _apply_image(self, pil_img):
        try:
            tk_img = ImageTk.PhotoImage(pil_img)
            self.label.configure(image=tk_img, text="")
            self.label._img_ref = tk_img
        except tk.TclError:
            pass

    def _post_status(self, text, ok):
        try:
            self.label.after(0, self.on_status, text, ok)
        except RuntimeError:
            pass


# ============================================================
# UI helpers
# ============================================================

def panel_header(parent, text, accent=ACCENT):
    """Section header: bold title + thin accent rule underneath."""
    f = tk.Frame(parent, bg=PANEL)
    inner = tk.Frame(f, bg=PANEL)
    inner.pack(fill=tk.X, padx=14, pady=(10, 4))
    tk.Label(inner, text=text, bg=PANEL, fg=TEXT,
             font=("Segoe UI", 11, "bold")).pack(anchor="w")
    bar = tk.Frame(f, bg=accent, height=2)
    bar.pack(fill=tk.X, padx=14, pady=(0, 8))
    return f


def hover_button(parent, text, bg, bg_hover, fg="white", **kw):
    btn = tk.Button(parent, text=text, bg=bg, fg=fg,
                    activebackground=bg_hover, activeforeground="white",
                    bd=0, relief=tk.FLAT, cursor="hand2",
                    highlightthickness=0, **kw)
    btn.bind("<Enter>", lambda _e: btn.configure(bg=bg_hover))
    btn.bind("<Leave>", lambda _e: btn.configure(bg=bg))
    return btn


# ============================================================
# Main UI
# ============================================================

class RoverRacingUI:
    def __init__(self, root):
        self.root = root
        root.title("Rover Control v3")
        root.configure(bg=BG)
        root.minsize(820, 1140)

        settings = load_settings()
        self.pi_host = settings.get("pi_host", DEFAULT_PI_HOST)

        try:
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1
            )
        except AttributeError:
            self.client = mqtt.Client()
        self.client.username_pw_set(USERNAME, PASSWORD)
        self.client.tls_set()
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.connected = False

        self.steer_pos = 0
        self.speed = 200
        self.steer_mode = tk.StringVar(value="ACKERMANN")
        self.auto_center = tk.BooleanVar(value=True)

        self.status_var = tk.StringVar(value="Disconnected")
        self.angle_label_var = tk.StringVar(value="Servo  90°  •  Straight")
        self.drive_label_var = tk.StringVar(value="IDLE")

        self.servo_offsets = {ch: 0 for ch in SERVO_CHANNELS}
        self.calib_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "servo_calibration.json"
        )
        self._load_calibration()

        self._pending_steer = False
        self._last_sent = {}
        self._held_drive = None
        self.speed_btns = {}
        self.speed_borders = {}

        self._build_ui()
        self._bind_keys()
        self._refresh_steer_visuals()
        self._refresh_speedo()
        self._connect_mqtt()

        self.camera = CameraStream(self.cam_label, self._set_cam_status)
        self.camera.configure_url(self._stream_url())
        self.camera.start()

    # ---------- MQTT ----------
    def _connect_mqtt(self):
        try:
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_start()
        except Exception as e:
            messagebox.showerror("MQTT", str(e))

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            self.status_var.set(f"Connect rc={rc}")
            return
        self.connected = True
        self.status_var.set("CONNECTED")
        self.status_dot.itemconfig("dot", fill=GOOD)
        self.status_label.configure(fg=GOOD)
        self._push_offsets_to_arduino()
        self._set_speed_mode(self.speed, push=True)

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.status_var.set("DISCONNECTED")
        self.status_dot.itemconfig("dot", fill=BAD)
        self.status_label.configure(fg=BAD)

    def _send(self, cmd):
        if self.connected:
            self.client.publish(TOPIC, cmd, qos=0)
            self._log(f">> {cmd.strip()}")
        else:
            self._log(f"[OFFLINE] {cmd.strip()}")

    # ---------- Camera ----------
    def _stream_url(self):
        return f"http://{self.pi_host}:{PI_STREAM_PORT}/stream"

    def _on_pi_host_change(self):
        new_host = self.pi_host_var.get().strip()
        if not new_host or new_host == self.pi_host:
            return
        self.pi_host = new_host
        save_settings({"pi_host": new_host})
        self.camera.configure_url(self._stream_url())
        self.camera.restart()

    def _on_stream_toggle(self):
        if self.stream_enabled.get():
            self.camera.configure_url(self._stream_url())
            self.camera.start()
        else:
            self.camera.stop()
            self._set_cam_status("OFF", ok=False)
            self.cam_label.configure(image=self._cam_placeholder,
                                     text="NO SIGNAL")

    def _set_cam_status(self, text, ok):
        self.cam_status_var.set(text)
        self.cam_status_lbl.configure(fg=GOOD if ok else BAD)

    # ---------- Calibration ----------
    def _load_calibration(self):
        if not os.path.exists(self.calib_file):
            return
        try:
            with open(self.calib_file, "r") as f:
                data = json.load(f)
            for ch in SERVO_CHANNELS:
                self.servo_offsets[ch] = int(data.get(str(ch), 0))
        except Exception:
            pass

    def _push_offsets_to_arduino(self):
        for ch, off in self.servo_offsets.items():
            self._send(f"OFST:{ch}:{off}\n")

    # ---------- Steering ----------
    def _steer_to_angles(self, steer):
        # User convention: servo 0° = max RIGHT, 180° = max LEFT, 90° = straight.
        # Slider: -90 = full LEFT, +90 = full RIGHT.
        front = max(0, min(180, 90 - int(steer)))
        rear  = max(0, min(180, 90 + int(steer)))
        if self.steer_mode.get() == "CRAB":
            return {ch: front for ch in SERVO_CHANNELS}
        return {0: front, 4: front, 1: 90, 5: 90, 2: rear, 6: rear}

    def _on_steer_change(self, value):
        self.steer_pos = int(value)
        self._refresh_steer_visuals()
        self._schedule_steer_send()

    def _on_steer_release(self):
        if self.auto_center.get():
            self.steer_pos = 0
            self.steer_bar.set_value(0)
            self._refresh_steer_visuals()
            self._schedule_steer_send()

    def _quick_steer(self, value):
        self.steer_pos = int(value)
        self.steer_bar.set_value(value)
        self._refresh_steer_visuals()
        self._schedule_steer_send()

    def _refresh_steer_visuals(self):
        front = self._steer_to_angles(self.steer_pos)[0]
        if front == 90:
            self.angle_label_var.set("Servo  90°  •  Straight")
        elif front < 90:
            self.angle_label_var.set(f"Servo  {front}°  •  Right")
        else:
            self.angle_label_var.set(f"Servo  {front}°  •  Left")
        self.wheel.set_steer(self.steer_pos)

    def _schedule_steer_send(self):
        if self._pending_steer:
            return
        self._pending_steer = True
        self.root.after(STEER_THROTTLE_MS, self._do_steer_send)

    def _do_steer_send(self):
        self._pending_steer = False
        angles = self._steer_to_angles(self.steer_pos)
        for ch, ang in angles.items():
            if self._last_sent.get(ch) == ang:
                continue
            physical = max(0, min(180, ang + self.servo_offsets[ch]))
            self._send(f"{ch}:{physical}\n")
            self._last_sent[ch] = ang

    # ---------- Speed ----------
    def _set_speed_mode(self, value, push=False):
        self.speed = value
        if push or self.connected:
            self._send(f"SPD:{value}\n")
        self._refresh_speed_btns()
        self._refresh_speedo()

    def _refresh_speed_btns(self):
        for name, val, color in SPEED_MODES:
            border = self.speed_borders[name]
            btn = self.speed_btns[name]
            if val == self.speed:
                border.configure(bg=color)
                btn.configure(bg=PANEL_HI, fg=color)
            else:
                border.configure(bg=BORDER)
                btn.configure(bg=PANEL, fg=TEXT_DIM)

    def _refresh_speedo(self):
        label = ""
        for name, val, _c in SPEED_MODES:
            if val == self.speed:
                label = name
                break
        self.speedo.set_value(self.speed, label=label)

    # ---------- Drive ----------
    def _drive_press(self, cmd):
        if self._held_drive == cmd:
            return
        self._held_drive = cmd
        if cmd == "W":
            self.drive_label_var.set("FORWARD")
            self.led.set_color(GOOD)
        else:
            self.drive_label_var.set("REVERSE")
            self.led.set_color(WARN)
        self._send(f"{cmd}\n")

    def _drive_release(self, cmd):
        if self._held_drive == cmd:
            self._held_drive = None
            self.drive_label_var.set("IDLE")
            self.led.set_color("#3a4148")
            self._send("H\n")

    def _drive_press_kb(self, cmd):
        if self._held_drive == cmd:
            return
        self._held_drive = cmd
        if cmd == "W":
            self.drive_label_var.set("FORWARD")
            self.led.set_color(GOOD)
        else:
            self.drive_label_var.set("REVERSE")
            self.led.set_color(WARN)
        self._send(f"{cmd}\n")

    def _emergency_stop(self):
        self._held_drive = None
        self.drive_label_var.set("STOPPED")
        self.led.set_color(BAD)
        self._send("H\n")

    # ---------- Keyboard ----------
    def _bind_keys(self):
        self.root.bind("<KeyPress-w>", lambda _e: self._drive_press_kb("W"))
        self.root.bind("<KeyPress-W>", lambda _e: self._drive_press_kb("W"))
        self.root.bind("<KeyPress-s>", lambda _e: self._drive_press_kb("S"))
        self.root.bind("<KeyPress-S>", lambda _e: self._drive_press_kb("S"))
        self.root.bind("<space>",  lambda _e: self._emergency_stop())
        self.root.bind("<Escape>", lambda _e: self._emergency_stop())
        self.root.bind("<Left>",  lambda _e: self._quick_steer(max(-90, self.steer_pos - 10)))
        self.root.bind("<Right>", lambda _e: self._quick_steer(min(90,  self.steer_pos + 10)))
        self.root.bind("<Down>",  lambda _e: self._quick_steer(0))
        for i, (_, val, _c) in enumerate(SPEED_MODES, start=1):
            self.root.bind(str(i), lambda _e, v=val: self._set_speed_mode(v))

    # ---------- Logging ----------
    def _log(self, msg):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        if int(self.log_text.index("end-1c").split(".")[0]) > 250:
            self.log_text.delete("1.0", "100.0")
        self.log_text.configure(state=tk.DISABLED)

    # ---------- UI build ----------
    def _build_ui(self):
        # ===== Top bar =====
        top = tk.Frame(self.root, bg=BG, height=58)
        top.pack(fill=tk.X)
        top.pack_propagate(False)

        tk.Label(top, text="◣", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 22)).pack(side=tk.LEFT, padx=(16, 6))
        tk.Label(top, text="ROVER RACING", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(top, text="v3", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(0, 20),
                                             pady=(8, 0))

        # Mode selector
        mode_box = tk.Frame(top, bg=BG)
        mode_box.pack(side=tk.RIGHT, padx=14)
        tk.Label(mode_box, text="STEER MODE", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="e")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Dark.TCombobox",
                        fieldbackground=PANEL_HI, background=PANEL_HI,
                        foreground=TEXT, arrowcolor=ACCENT,
                        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        mode_menu = ttk.Combobox(mode_box, textvariable=self.steer_mode,
                                 values=["ACKERMANN", "CRAB"], state="readonly",
                                 width=11, style="Dark.TCombobox")
        mode_menu.pack()
        mode_menu.bind("<<ComboboxSelected>>",
                       lambda _e: (self._last_sent.clear(),
                                   self._refresh_steer_visuals(),
                                   self._schedule_steer_send()))

        # Auto-center
        ac_box = tk.Frame(top, bg=BG)
        ac_box.pack(side=tk.RIGHT, padx=14)
        tk.Label(ac_box, text="AUTO", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="e")
        tk.Checkbutton(ac_box, text="Recenter",
                       variable=self.auto_center,
                       bg=BG, fg=TEXT, selectcolor=PANEL,
                       activebackground=BG, activeforeground=TEXT,
                       font=("Segoe UI", 9)).pack()

        # MQTT status
        st_box = tk.Frame(top, bg=BG)
        st_box.pack(side=tk.RIGHT, padx=20)
        tk.Label(st_box, text="MQTT", bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="e")
        st_inner = tk.Frame(st_box, bg=BG)
        st_inner.pack()
        self.status_dot = tk.Canvas(st_inner, width=14, height=14, bg=BG,
                                    highlightthickness=0)
        self.status_dot.create_oval(2, 2, 13, 13, fill=BAD,
                                    outline="", tags="dot")
        self.status_dot.pack(side=tk.LEFT, padx=(0, 6), pady=(2, 0))
        self.status_label = tk.Label(st_inner, textvariable=self.status_var,
                                     bg=BG, fg=BAD,
                                     font=("Consolas", 10, "bold"))
        self.status_label.pack(side=tk.LEFT)

        # Top divider
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        # ===== Camera panel =====
        cam = tk.Frame(self.root, bg=PANEL)
        cam.pack(fill=tk.X, padx=10, pady=(10, 6))
        panel_header(cam, "CAMERA   ·   live from Pi",
                     accent=ACCENT_2).pack(fill=tk.X)

        cam_row = tk.Frame(cam, bg=PANEL)
        cam_row.pack(fill=tk.X, padx=14, pady=(0, 12))

        self._cam_placeholder = tk.PhotoImage(
            width=CAMERA_DISPLAY_W, height=CAMERA_DISPLAY_H
        )
        self.cam_label = tk.Label(cam_row, bg="#000",
                                  image=self._cam_placeholder,
                                  text="NO SIGNAL",
                                  fg=TEXT_DIM,
                                  font=("Consolas", 14, "bold"),
                                  compound="center",
                                  bd=1, relief=tk.FLAT,
                                  highlightthickness=1,
                                  highlightbackground=BORDER)
        self.cam_label.pack(side=tk.LEFT, padx=(4, 18))

        ctrl = tk.Frame(cam_row, bg=PANEL)
        ctrl.pack(side=tk.LEFT, fill=tk.Y, anchor="n", pady=(2, 0))

        tk.Label(ctrl, text="PI HOST", bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        host_row = tk.Frame(ctrl, bg=PANEL)
        host_row.pack(anchor="w", pady=(2, 8))
        self.pi_host_var = tk.StringVar(value=self.pi_host)
        host_entry = tk.Entry(host_row, textvariable=self.pi_host_var,
                              bg=PANEL_HI, fg=TEXT, insertbackground=TEXT,
                              relief=tk.FLAT, font=("Consolas", 11),
                              width=18, bd=0, highlightthickness=1,
                              highlightcolor=ACCENT,
                              highlightbackground=BORDER)
        host_entry.pack(side=tk.LEFT, ipady=4)
        host_entry.bind("<Return>", lambda _e: self._on_pi_host_change())
        hover_button(host_row, "↻", "#2a3340", "#3a4350",
                     fg=TEXT, font=("Segoe UI", 10, "bold"),
                     padx=10, pady=4,
                     command=self._on_pi_host_change).pack(side=tk.LEFT,
                                                            padx=(6, 0))

        tk.Label(ctrl, text="STATUS", bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 0))
        self.cam_status_var = tk.StringVar(value="Disconnected")
        self.cam_status_lbl = tk.Label(ctrl, textvariable=self.cam_status_var,
                                        bg=PANEL, fg=BAD,
                                        font=("Consolas", 11, "bold"))
        self.cam_status_lbl.pack(anchor="w", pady=(2, 10))

        self.stream_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(ctrl, text="Stream ON",
                       variable=self.stream_enabled,
                       bg=PANEL, fg=TEXT, selectcolor=PANEL,
                       activebackground=PANEL, activeforeground=TEXT,
                       font=("Segoe UI", 10, "bold"),
                       command=self._on_stream_toggle).pack(anchor="w")

        tk.Label(ctrl,
                 text=f"Stream URL:\nhttp://<host>:{PI_STREAM_PORT}/stream",
                 bg=PANEL, fg=TEXT_DIM, justify="left",
                 font=("Consolas", 8)).pack(anchor="w", pady=(10, 0))

        # ===== Steering panel =====
        steer = tk.Frame(self.root, bg=PANEL)
        steer.pack(fill=tk.X, padx=10, pady=(10, 6))
        panel_header(steer, "STEERING", accent=ACCENT).pack(fill=tk.X)

        wheel_row = tk.Frame(steer, bg=PANEL)
        wheel_row.pack(pady=(2, 4))
        self.wheel = SteeringWheel(wheel_row)
        self.wheel.pack(side=tk.LEFT, padx=(20, 24), pady=4)

        info = tk.Frame(wheel_row, bg=PANEL)
        info.pack(side=tk.LEFT, anchor="w")
        tk.Label(info, text="WHEEL ANGLE", bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(info, textvariable=self.angle_label_var,
                 bg=PANEL, fg=ACCENT,
                 font=("Consolas", 18, "bold")).pack(anchor="w", pady=(4, 14))
        tk.Label(info, text="0° = max right",
                 bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(info, text="90° = straight",
                 bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(info, text="180° = max left",
                 bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(anchor="w")

        # Steering bar
        bar_row = tk.Frame(steer, bg=PANEL)
        bar_row.pack(fill=tk.X, padx=24, pady=(2, 6))
        tk.Label(bar_row, text="LEFT", bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold"), width=5).pack(side=tk.LEFT)
        self.steer_bar = SteeringBar(bar_row, width=560,
                                     on_change=self._on_steer_change,
                                     on_release=self._on_steer_release)
        self.steer_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        tk.Label(bar_row, text="RIGHT", bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold"), width=5).pack(side=tk.LEFT)

        # Quick presets
        quick = tk.Frame(steer, bg=PANEL)
        quick.pack(pady=(2, 12))
        for label, val in [("◀◀ FULL", -90), ("◀ LEFT", -45),
                           ("● CENTER", 0),
                           ("RIGHT ▶", 45), ("FULL ▶▶", 90)]:
            color = ACCENT if val == 0 else PANEL_HI
            hover = "#1565c0" if val == 0 else ROW
            fg = "#000" if val == 0 else TEXT
            hover_button(quick, label, color, hover, fg=fg, width=11,
                         font=("Segoe UI", 10, "bold"), pady=6,
                         command=lambda v=val: self._quick_steer(v)
                         ).pack(side=tk.LEFT, padx=4)

        # ===== Throttle panel =====
        thr = tk.Frame(self.root, bg=PANEL)
        thr.pack(fill=tk.X, padx=10, pady=6)
        panel_header(thr, "THROTTLE", accent=ACCENT_2).pack(fill=tk.X)

        thr_row = tk.Frame(thr, bg=PANEL)
        thr_row.pack(fill=tk.X, padx=14, pady=(0, 12))

        self.speedo = Speedometer(thr_row)
        self.speedo.pack(side=tk.LEFT, padx=(6, 18))

        spd_grid = tk.Frame(thr_row, bg=PANEL)
        spd_grid.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        tk.Label(spd_grid, text="SPEED MODE", bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 6))

        pills = tk.Frame(spd_grid, bg=PANEL)
        pills.pack(anchor="w")
        for name, val, color in SPEED_MODES:
            border = tk.Frame(pills, bg=BORDER)
            border.pack(side=tk.LEFT, padx=4, pady=2)
            btn = tk.Button(border, text=f"{name}\n{val}",
                            bg=PANEL, fg=TEXT_DIM,
                            font=("Segoe UI", 10, "bold"),
                            width=9, height=2,
                            bd=0, relief=tk.FLAT, cursor="hand2",
                            activebackground=PANEL_HI,
                            activeforeground=color,
                            command=lambda v=val: self._set_speed_mode(v))
            btn.pack(padx=2, pady=2)
            self.speed_borders[name] = border
            self.speed_btns[name] = btn

        tk.Label(spd_grid, text="Press 1–4 to switch",
                 bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))

        # ===== Drive panel =====
        drv = tk.Frame(self.root, bg=PANEL)
        drv.pack(fill=tk.X, padx=10, pady=6)
        panel_header(drv, "DRIVE   ·   hold-to-drive", accent=GOOD).pack(fill=tk.X)

        drv_row = tk.Frame(drv, bg=PANEL)
        drv_row.pack(fill=tk.X, padx=14, pady=(0, 14))

        # LED + state
        led_box = tk.Frame(drv_row, bg=PANEL)
        led_box.pack(side=tk.LEFT, padx=(8, 22))
        self.led = StateLED(led_box)
        self.led.pack(pady=(4, 4))
        tk.Label(led_box, text="STATE", bg=PANEL, fg=TEXT_DIM,
                 font=("Segoe UI", 8, "bold")).pack()
        tk.Label(led_box, textvariable=self.drive_label_var,
                 bg=PANEL, fg=TEXT,
                 font=("Consolas", 13, "bold")).pack()

        # Drive buttons
        btns = tk.Frame(drv_row, bg=PANEL)
        btns.pack(side=tk.LEFT, fill=tk.X, expand=True)

        fwd = hover_button(btns, "▲   FORWARD   (W)",
                           "#1f8a3a", "#28a745",
                           font=("Segoe UI", 12, "bold"),
                           pady=14)
        fwd.pack(fill=tk.X, pady=4)
        fwd.bind("<ButtonPress-1>",   lambda _e: self._drive_press("W"))
        fwd.bind("<ButtonRelease-1>", lambda _e: self._drive_release("W"))

        stop = hover_button(btns, "■   STOP   (Space)",
                            "#a8261d", "#c62828",
                            font=("Segoe UI", 12, "bold"),
                            pady=10,
                            command=self._emergency_stop)
        stop.pack(fill=tk.X, pady=4)

        rev = hover_button(btns, "▼   REVERSE   (S)",
                           "#b85a00", "#e65100",
                           font=("Segoe UI", 12, "bold"),
                           pady=14)
        rev.pack(fill=tk.X, pady=4)
        rev.bind("<ButtonPress-1>",   lambda _e: self._drive_press("S"))
        rev.bind("<ButtonRelease-1>", lambda _e: self._drive_release("S"))

        # ===== Emergency stop strip =====
        es = hover_button(self.root,
                          "🛑   EMERGENCY  STOP   🛑",
                          "#7a0e0e", "#b71c1c",
                          font=("Segoe UI", 14, "bold"),
                          pady=10,
                          command=self._emergency_stop)
        es.pack(fill=tk.X, padx=10, pady=(6, 4))

        # Keys hint
        keys_text = ("←/→  steer 10°    ↓  center    "
                     "W  forward    S  reverse    "
                     "Space/Esc  STOP    1-4  speed mode")
        tk.Label(self.root, text=keys_text, bg=BG, fg=TEXT_DIM,
                 font=("Segoe UI", 8)).pack(pady=(2, 2))

        # ===== Log =====
        log_wrap = tk.Frame(self.root, bg=PANEL)
        log_wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 8))
        panel_header(log_wrap, "LOG", accent=BORDER).pack(fill=tk.X)
        self.log_text = tk.Text(log_wrap, height=5, bg="#05080c", fg=GOOD,
                                font=("Consolas", 9), state=tk.DISABLED,
                                wrap="none", bd=0, relief=tk.FLAT,
                                insertbackground=TEXT)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))

    def on_close(self):
        try:
            self.camera.stop()
        except Exception:
            pass
        try:
            self._send("H\n")
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = RoverRacingUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
