import paho.mqtt.client as mqtt
import ssl
import serial
import serial.tools.list_ports

# Thông tin MQTT broker
BROKER = "80d38917ab9144ccb7ecee5f086e00f9.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "datn2025"
PASSWORD = "Datn2025"
TOPIC = "car/control"

# Khai báo serial
ser = serial.Serial()
ser.baudrate = 9600
ser.timeout = 1

# Biến trạng thái
mqtt_connected = False
arduino_connected = False

# --- Hàm dò tìm Arduino ---
def find_arduino():
    global arduino_connected
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        try:
            ser.port = p.device
            ser.open()
            if ser.isOpen():
                print(" Arduino kết nối tại", p.device)
                arduino_connected = True
                return True
        except Exception:
            pass
    arduino_connected = False
    return False

# --- Callback MQTT ---
def on_connect(client, userdata, flags, rc, properties=None):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print(" Kết nối MQTT thành công!")
        client.subscribe(TOPIC)
        print(f"📡 Đã subscribe topic: {TOPIC}")
    else:
        print(" Kết nối MQTT thất bại. Mã lỗi:", rc)

def on_message(client, userdata, msg):
    global mqtt_connected, arduino_connected
    command = msg.payload.decode().strip()
    print(f" Nhận từ {msg.topic}: {command}")

    if not mqtt_connected:
        print("⚠ MQTT chưa kết nối, bỏ qua lệnh")
        return

    # Nếu Arduino chưa kết nối -> thử dò lại ngay
    if not arduino_connected:
        print(" Thử kết nối lại Arduino...")
        if not find_arduino():
            print("⚠ Arduino chưa kết nối, bỏ qua lệnh")
            return

    # Nếu Arduino kết nối thành công thì gửi lệnh
    if ser.is_open:
        ser.write((command + "\n").encode())
        print("➡ Đã gửi tới Arduino:", command)

# --- Main ---
client = mqtt.Client(client_id="raspberrypi", protocol=mqtt.MQTTv311)
client.enable_logger()
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
client.on_connect = on_connect
client.on_message = on_message

print("🔌 Đang kết nối tới broker...")
client.connect(BROKER, PORT, 60)

# Vòng lặp chính
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("⏹ Dừng chương trình")
finally:
    if ser.is_open:
        ser.close()
    client.disconnect()
