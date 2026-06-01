#!/usr/bin/env python3
"""
MJPEG webcam streamer for Raspberry Pi 4 with optional vision processing.

Endpoints:
  /          simple HTML page with <img src="/stream"> for browser testing
  /stream    multipart/x-mixed-replace MJPEG stream
  /health    JSON {"ok": true}

Modes (--mode):
  raw       (default) just stream the camera, no processing
  face      detect biggest face, draw a rectangle, and publish servo
            commands (J / L / K) to MQTT topic `car/control` so the
            rover steers toward the face. Forward motion is NOT
            commanded — drive W/S manually from the GUI.

Usage on the Pi:
    python3 pi_camera_stream.py
    python3 pi_camera_stream.py --mode face
    python3 pi_camera_stream.py --mode face --no-mqtt   # visualize only
    python3 pi_camera_stream.py --width 320 --height 240 --fps 10
    python3 pi_camera_stream.py --device 1
"""

import argparse
import atexit
import json
import math
import os
import signal
import ssl
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import cv2
except ImportError:
    print("ERROR: OpenCV (cv2) is not installed on this Pi.")
    print("Try one of:")
    print("  sudo apt install python3-opencv")
    print("  pip3 install opencv-python")
    sys.exit(1)


# MQTT config (must match Giao_dien_v3.py and pi_mqtt_bridge.py)
MQTT_BROKER = "80d38917ab9144ccb7ecee5f086e00f9.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "datn2025"
MQTT_PASSWORD = "Datn2025"
MQTT_TOPIC = "car/control"


_latest_jpeg = None
_latest_lock = threading.Lock()
_running = True
_mqtt_client = None  # set if a vision mode connects to MQTT


def make_mqtt_publisher():
    """Connect to HiveMQ and return (publish_fn, client) or (None, None)
    if paho-mqtt is missing or the connection fails."""
    global _mqtt_client
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("WARN: paho-mqtt not installed; running with --no-mqtt")
        return None, None

    try:
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="pi-vision",
        )
    except (AttributeError, TypeError):
        client = mqtt.Client(client_id="pi-vision")

    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED,
                   tls_version=ssl.PROTOCOL_TLSv1_2)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except Exception as e:
        print(f"WARN: MQTT connect failed ({e}); running with no MQTT")
        return None, None
    client.loop_start()
    _mqtt_client = client

    def publish(payload):
        if isinstance(payload, str):
            payload = payload.encode()
        client.publish(MQTT_TOPIC, payload, qos=0)

    print(f"MQTT publisher connected to {MQTT_BROKER}")
    return publish, client


# ----------------------------------------------------------------------
# Frame processors (--mode dispatch)
# ----------------------------------------------------------------------

class FrameProcessor:
    """Base: process(frame) returns the frame to encode."""
    def process(self, frame):
        return frame


class RawProcessor(FrameProcessor):
    pass


def find_haar_cascade(name="haarcascade_frontalface_default.xml"):
    """Locate a Haar cascade XML across the various places different
    OpenCV builds place it. Returns absolute path or None."""
    candidates = []
    try:
        candidates.append(cv2.data.haarcascades + name)
    except AttributeError:
        pass
    candidates += [
        f"/usr/share/opencv4/haarcascades/{name}",
        f"/usr/local/share/opencv4/haarcascades/{name}",
        f"/usr/share/opencv/haarcascades/{name}",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), name),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


class FaceProcessor(FrameProcessor):
    """Detect biggest face, draw overlay, publish J/L/K servo commands
    when the face crosses out of / into the centre deadzone."""

    def __init__(self, publish, deadzone_frac=0.16):
        self.publish = publish
        self.deadzone_frac = deadzone_frac
        cascade_path = find_haar_cascade()
        if cascade_path is None:
            raise RuntimeError(
                "Haar cascade XML not found. Install with:\n"
                "  sudo apt install opencv-data\n"
                "or copy haarcascade_frontalface_default.xml next to "
                "pi_camera_stream.py"
            )
        print(f"Using Haar cascade: {cascade_path}")
        self.detector = cv2.CascadeClassifier(cascade_path)
        if self.detector.empty():
            raise RuntimeError(
                f"Could not load Haar cascade at {cascade_path}"
            )
        self.last_cmd = None
        self.no_face_frames = 0

    def _send(self, cmd):
        if cmd == self.last_cmd:
            return
        self.last_cmd = cmd
        if self.publish is not None:
            self.publish(cmd + "\n")
            print(f"  -> publish {cmd}")

    def process(self, frame):
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self.detector.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60)
        )

        deadzone = int(w * self.deadzone_frac)
        cx_frame = w // 2

        # Always draw deadzone + crosshair
        cv2.line(frame, (cx_frame - deadzone, 0),
                 (cx_frame - deadzone, h), (0, 200, 200), 1)
        cv2.line(frame, (cx_frame + deadzone, 0),
                 (cx_frame + deadzone, h), (0, 200, 200), 1)
        cv2.line(frame, (cx_frame, h // 2 - 10),
                 (cx_frame, h // 2 + 10), (255, 255, 255), 1)
        cv2.line(frame, (cx_frame - 10, h // 2),
                 (cx_frame + 10, h // 2), (255, 255, 255), 1)

        status = "NO FACE"
        status_color = (0, 0, 255)

        if len(faces) > 0:
            self.no_face_frames = 0
            x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])
            cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)
            face_cx = x + fw // 2

            if face_cx < cx_frame - deadzone:
                self._send("J")  # small left
                status = "TURN LEFT  (J)"
                status_color = (0, 200, 255)
            elif face_cx > cx_frame + deadzone:
                self._send("L")  # small right
                status = "TURN RIGHT (L)"
                status_color = (0, 200, 255)
            else:
                self._send("K")  # centre wheels
                status = "CENTERED   (K)"
                status_color = (0, 255, 0)
        else:
            self.no_face_frames += 1
            # After ~1s of no face, recenter wheels (don't stop drive)
            if self.no_face_frames > 15:
                self._send("K")

        cv2.putText(frame, "MODE: FACE", (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, status, (10, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        return frame


class HandsProcessor(FrameProcessor):
    """MediaPipe Hands: tilt of wrist→middle-finger MCP becomes a
    continuous steering angle. Sends per-channel servo commands at
    a throttled rate, with EMA smoothing. Forward motion is NOT
    commanded — drive W/S manually from the GUI."""

    def __init__(self, publish, send_throttle_ms=60, ema_alpha=0.4,
                 max_steer=60):
        try:
            import mediapipe as mp
        except ImportError as e:
            raise RuntimeError(
                "mediapipe not installed. On the Pi:\n"
                "  pip install --break-system-packages mediapipe"
            ) from e
        print("Initializing MediaPipe Hands (model_complexity=0)...")
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=0,
        )

        self.publish = publish
        self.send_throttle = send_throttle_ms / 1000.0
        self.ema_alpha = ema_alpha
        self.max_steer = max_steer

        self.smooth_steer = 0.0
        self.last_send_t = 0.0
        self.last_sent = {}     # {ch: angle} de-dup per channel
        self.no_hand_frames = 0

        self.offsets = self._load_calibration()
        if self.offsets:
            print(f"Loaded servo calibration: {self.offsets}")
        else:
            print("No servo_calibration.json found next to script; "
                  "using zero offsets")

    @staticmethod
    def _load_calibration():
        cal_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "servo_calibration.json"
        )
        if not os.path.exists(cal_path):
            return {}
        try:
            with open(cal_path) as f:
                data = json.load(f)
            return {int(k): int(v) for k, v in data.items()}
        except Exception as e:
            print(f"WARN: could not parse {cal_path}: {e}")
            return {}

    def process(self, frame):
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self.hands.process(rgb)

        steer_raw = None
        if result.multi_hand_landmarks:
            self.no_hand_frames = 0
            hl = result.multi_hand_landmarks[0]
            self.mp_draw.draw_landmarks(
                frame, hl, self.mp_hands.HAND_CONNECTIONS,
                self.mp_styles.get_default_hand_landmarks_style(),
                self.mp_styles.get_default_hand_connections_style(),
            )
            wx = hl.landmark[0].x * w
            wy = hl.landmark[0].y * h
            mx = hl.landmark[9].x * w
            my = hl.landmark[9].y * h

            dx = mx - wx
            dy = my - wy
            tilt_rad = math.atan2(dx, -dy)
            tilt_deg = math.degrees(tilt_rad)
            steer_raw = max(-self.max_steer,
                            min(self.max_steer, tilt_deg))

            cv2.line(frame, (int(wx), int(wy)), (int(mx), int(my)),
                     (0, 255, 255), 3)
            cv2.circle(frame, (int(wx), int(wy)), 8, (0, 255, 0), -1)
            cv2.circle(frame, (int(mx), int(my)), 8, (255, 0, 255), -1)
        else:
            self.no_hand_frames += 1

        # EMA smoothing
        if steer_raw is not None:
            self.smooth_steer = (
                self.ema_alpha * steer_raw
                + (1 - self.ema_alpha) * self.smooth_steer
            )
        else:
            self.smooth_steer *= 0.85  # decay toward 0 on hand loss

        # Publish at throttled rate
        now = time.time()
        if (self.publish is not None
                and (now - self.last_send_t) >= self.send_throttle):
            self.last_send_t = now
            if self.no_hand_frames > 15:
                self._send_recenter()
            else:
                self._send_servos(int(self.smooth_steer))

        self._draw_hud(frame, steer_raw)
        return frame

    def _send_servos(self, steer):
        # Same Ackermann mapping as v3 GUI:
        # front (CH0/CH4) and rear (CH2/CH6) opposite, mids (CH1/CH5) at 90.
        front = max(0, min(180, 90 - steer))
        rear = max(0, min(180, 90 + steer))
        targets = {0: front, 4: front, 1: 90, 5: 90, 2: rear, 6: rear}
        for ch, ang in targets.items():
            physical = max(0, min(180, ang + self.offsets.get(ch, 0)))
            if self.last_sent.get(ch) == physical:
                continue
            self.publish(f"{ch}:{physical}\n")
            self.last_sent[ch] = physical

    def _send_recenter(self):
        # "K\n" applies servo offsets in firmware; no need to dedup
        # against per-channel state since K resets all six.
        if self.last_sent.get("__center__") is True:
            return
        self.publish("K\n")
        self.last_sent = {"__center__": True}

    def _draw_hud(self, frame, steer_raw):
        h, w = frame.shape[:2]
        steer_int = int(self.smooth_steer)
        cv2.putText(frame, "MODE: HANDS", (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        color = (0, 255, 255) if steer_raw is not None else (0, 0, 255)
        label = (f"STEER: {steer_int:+d} deg"
                 if steer_raw is not None else "NO HAND")
        cv2.putText(frame, label, (10, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Steering indicator bar at top
        cx = w // 2
        bar_top = 40
        bar_h = 8
        bar_half = 100
        cv2.rectangle(frame, (cx - bar_half, bar_top),
                      (cx + bar_half, bar_top + bar_h),
                      (60, 60, 60), -1)
        cv2.line(frame, (cx, bar_top - 3),
                 (cx, bar_top + bar_h + 3), (200, 200, 200), 1)
        knob_x = cx + int(self.smooth_steer / self.max_steer * bar_half)
        cv2.circle(frame, (knob_x, bar_top + bar_h // 2), 8,
                   color, -1)


def shutdown_mqtt(publish_fn):
    """On clean exit, recenter wheels and disconnect MQTT."""
    if publish_fn is not None:
        try:
            publish_fn("K\n")
            time.sleep(0.1)
        except Exception:
            pass
    if _mqtt_client is not None:
        try:
            _mqtt_client.loop_stop()
            _mqtt_client.disconnect()
        except Exception:
            pass


def capture_loop(device, width, height, fps, quality, processor):
    global _latest_jpeg
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        print(f"ERROR: cannot open camera /dev/video{device}")
        print("Check: ls /dev/video*  and  v4l2-ctl --list-devices")
        sys.exit(2)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera opened: requested {width}x{height}@{fps}, "
          f"got {actual_w}x{actual_h}")

    encode = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    target_dt = 1.0 / fps if fps > 0 else 0.0

    while _running:
        t0 = time.time()
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.05)
            continue
        try:
            frame = processor.process(frame)
        except Exception as e:
            print(f"processor error: {e}")
        ok, jpeg = cv2.imencode(".jpg", frame, encode)
        if ok:
            with _latest_lock:
                _latest_jpeg = jpeg.tobytes()
        dt = time.time() - t0
        if dt < target_dt:
            time.sleep(target_dt - dt)

    cap.release()
    print("Camera released")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return  # silence default access log

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve_index()
        elif self.path == "/stream":
            self._serve_stream()
        elif self.path == "/health":
            self._serve_health()
        else:
            self.send_error(404)

    def _serve_index(self):
        body = (
            b"<!doctype html><title>Rover Camera</title>"
            b"<body style='margin:0;background:#000;color:#fff;"
            b"font-family:sans-serif'>"
            b"<h3 style='padding:8px'>Rover Camera Stream</h3>"
            b"<img src='/stream' style='max-width:100%'>"
            b"</body>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_health(self):
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_stream(self):
        self.send_response(200)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header(
            "Content-Type", "multipart/x-mixed-replace; boundary=frame"
        )
        self.end_headers()
        try:
            while _running:
                with _latest_lock:
                    jpeg = _latest_jpeg
                if jpeg is None:
                    time.sleep(0.05)
                    continue
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(
                    f"Content-Length: {len(jpeg)}\r\n\r\n".encode()
                )
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
                time.sleep(0.04)
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    global _running
    p = argparse.ArgumentParser(description="Pi webcam MJPEG streamer")
    p.add_argument("--device", type=int, default=0,
                   help="V4L2 device index (default 0 -> /dev/video0)")
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--fps", type=int, default=15)
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--quality", type=int, default=70,
                   help="JPEG quality 1-100 (default 70)")
    p.add_argument("--mode", choices=["raw", "face", "hands"], default="raw",
                   help="Vision mode (default: raw)")
    p.add_argument("--no-mqtt", action="store_true",
                   help="Disable MQTT publishing in vision modes "
                        "(visualize only)")
    p.add_argument("--deadzone", type=float, default=0.16,
                   help="Face mode: centre deadzone as fraction of "
                        "frame width (default 0.16)")
    p.add_argument("--ema", type=float, default=0.4,
                   help="Hand mode: EMA smoothing alpha 0-1 (lower = "
                        "smoother but laggier; default 0.4)")
    p.add_argument("--max-steer", type=int, default=60,
                   help="Hand mode: clip steering angle (deg) magnitude "
                        "(default 60)")
    args = p.parse_args()

    publisher = None
    if args.mode != "raw" and not args.no_mqtt:
        publisher, _ = make_mqtt_publisher()

    if args.mode == "raw":
        processor = RawProcessor()
    elif args.mode == "face":
        processor = FaceProcessor(publisher, deadzone_frac=args.deadzone)
    elif args.mode == "hands":
        processor = HandsProcessor(publisher, ema_alpha=args.ema,
                                   max_steer=args.max_steer)
    else:
        raise SystemExit(f"unknown mode: {args.mode}")

    print(f"Vision mode: {args.mode}"
          + ("  (MQTT publishing OFF)" if args.mode != "raw" and publisher is None
             else ""))

    atexit.register(shutdown_mqtt, publisher)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    cap_thread = threading.Thread(
        target=capture_loop,
        args=(args.device, args.width, args.height, args.fps,
              args.quality, processor),
        daemon=True,
    )
    cap_thread.start()

    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"Serving on http://0.0.0.0:{args.port}/")
    print(f"  Browser test : http://<pi-ip>:{args.port}/")
    print(f"  MJPEG stream : http://<pi-ip>:{args.port}/stream")
    print(f"  Health check : http://<pi-ip>:{args.port}/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        _running = False
        server.shutdown()
        time.sleep(0.3)


if __name__ == "__main__":
    main()
