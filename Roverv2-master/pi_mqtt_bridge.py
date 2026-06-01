#!/usr/bin/env python3
"""
Raspberry Pi MQTT-to-Serial bridge for Roverv2.

Subscribes to topic `car/control` on HiveMQ Cloud (TLS) and forwards
each message payload verbatim to the Arduino Mega 2560 over USB serial.
The PC GUI already terminates multi-character commands with '\n', so
this bridge does not modify payloads.

Run on the Pi:
    python3 pi_mqtt_bridge.py
    python3 pi_mqtt_bridge.py --port /dev/ttyACM0      # if Arduino is on ACM
    python3 pi_mqtt_bridge.py --port /dev/ttyUSB0 -v   # verbose logging
"""

import argparse
import logging
import ssl
import sys
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("ERROR: paho-mqtt not installed.")
    print("Install: sudo apt install python3-paho-mqtt")
    sys.exit(1)

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed.")
    print("Install: sudo apt install python3-serial")
    sys.exit(1)


BROKER = "80d38917ab9144ccb7ecee5f086e00f9.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "datn2025"
PASSWORD = "Datn2025"
TOPIC = "car/control"

DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 9600


log = logging.getLogger("bridge")


class Bridge:
    def __init__(self, serial_port, baud):
        self.serial_port = serial_port
        self.baud = baud
        self.ser = None
        self.client = None

    def open_serial(self):
        while self.ser is None:
            try:
                self.ser = serial.Serial(self.serial_port, self.baud,
                                         timeout=0.1)
                log.info("Serial open: %s @ %d", self.serial_port, self.baud)
            except (serial.SerialException, OSError) as e:
                log.warning("Serial open failed (%s); retrying in 2s", e)
                time.sleep(2)

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            log.info("MQTT connected; subscribing to %s", TOPIC)
            client.subscribe(TOPIC)
        else:
            log.error("MQTT connect failed rc=%s", rc)

    def on_disconnect(self, client, userdata, *args):
        log.warning("MQTT disconnected; auto-reconnect via loop_forever")

    def on_message(self, client, userdata, msg):
        payload = msg.payload
        log.info("RX %s: %r", msg.topic, payload)
        if self.ser is None or not self.ser.is_open:
            log.warning("Serial not open; dropping message")
            return
        try:
            self.ser.write(payload)
        except (serial.SerialException, OSError) as e:
            log.error("Serial write failed: %s; reopening", e)
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
            self.open_serial()

    def run(self):
        self.open_serial()
        try:
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id="rover-bridge",
            )
        except (AttributeError, TypeError):
            self.client = mqtt.Client(client_id="rover-bridge")
        self.client.username_pw_set(USERNAME, PASSWORD)
        self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED,
                            tls_version=ssl.PROTOCOL_TLSv1_2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        log.info("Connecting to %s:%d", BROKER, PORT)
        self.client.connect(BROKER, PORT, keepalive=60)
        self.client.loop_forever(retry_first_connection=True)


def main():
    p = argparse.ArgumentParser(description="Rover MQTT -> Serial bridge")
    p.add_argument("--port", default=DEFAULT_SERIAL_PORT,
                   help="Serial device (default /dev/ttyUSB0)")
    p.add_argument("--baud", type=int, default=DEFAULT_BAUD,
                   help="Baud rate (default 9600)")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="DEBUG-level logging")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    Bridge(args.port, args.baud).run()


if __name__ == "__main__":
    main()
