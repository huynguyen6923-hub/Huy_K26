import tkinter as tk
from tkinter import PhotoImage

import paho.mqtt.client as mqtt

BROKER = "80d38917ab9144ccb7ecee5f086e00f9.s1.eu.hivemq.cloud"   
PORT = 8883
USERNAME = "datn2025"
PASSWORD = "Datn2025"
TOPIC = "car/control"

# Kết nối MQTT
client = mqtt.Client()
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set()  
client.connect(BROKER, PORT, 60)
client.loop_start()

def send_command(cmd):
    """Gửi lệnh lên HiveMQ"""
    client.publish(TOPIC, cmd, qos=0)
    print(f"Đã gửi lệnh: {cmd}")

root = tk.Tk()
root.title("Giao diện điều khiển xe")

# Load ảnh icon 
icons = {
    "Q": PhotoImage(file="icons/q.png"),
    "W": PhotoImage(file="icons/w.png"),
    "E": PhotoImage(file="icons/e.png"),
    "R": PhotoImage(file="icons/r.png"),
    "A": PhotoImage(file="icons/a.png"),
    "S": PhotoImage(file="icons/s.png"),
    "D": PhotoImage(file="icons/d.png"),
    "F": PhotoImage(file="icons/f.png"),
    "U": PhotoImage(file="icons/u.png"),
    "O": PhotoImage(file="icons/o.png"),
    "J": PhotoImage(file="icons/j.png"),
    "K": PhotoImage(file="icons/k.png"),
    "L": PhotoImage(file="icons/l.png"),
    "STOP": PhotoImage(file="icons/stop.png"),
}

# Khung bên trái
frame_left = tk.Frame(root, bg="black")
frame_left.grid(row=0, column=0, padx=5, pady=50)

# Hàng 1
tk.Button(frame_left, image=icons["Q"], command=lambda: send_command("Q")).grid(row=0, column=0, padx=5, pady=5)
tk.Button(frame_left, image=icons["W"], command=lambda: send_command("W")).grid(row=0, column=1, padx=5, pady=5)
tk.Button(frame_left, image=icons["E"], command=lambda: send_command("E")).grid(row=0, column=2, padx=5, pady=5)
tk.Button(frame_left, image=icons["R"], command=lambda: send_command("R")).grid(row=0, column=3, padx=5, pady=5)

# Hàng 2
tk.Button(frame_left, image=icons["A"], command=lambda: send_command("A")).grid(row=1, column=0, padx=5, pady=5)
tk.Button(frame_left, image=icons["S"], command=lambda: send_command("S")).grid(row=1, column=1, padx=5, pady=5)
tk.Button(frame_left, image=icons["D"], command=lambda: send_command("D")).grid(row=1, column=2, padx=5, pady=5)
tk.Button(frame_left, image=icons["F"], command=lambda: send_command("F")).grid(row=1, column=3, padx=5, pady=5)

# Khung bên phải
frame_right = tk.Frame(root, bg="black")
frame_right.grid(row=0, column=1, padx=5, pady=5)

tk.Button(frame_right, image=icons["U"], command=lambda: send_command("U")).grid(row=0, column=0, padx=5, pady=5)
tk.Button(frame_right, image=icons["O"], command=lambda: send_command("O")).grid(row=0, column=1, padx=5, pady=5)

tk.Button(frame_right, image=icons["J"], command=lambda: send_command("J")).grid(row=1, column=0, padx=5, pady=5)
tk.Button(frame_right, image=icons["K"], command=lambda: send_command("K")).grid(row=1, column=1, padx=5, pady=5)
tk.Button(frame_right, image=icons["L"], command=lambda: send_command("L")).grid(row=1, column=2, padx=5, pady=5)

# Nút STOP
tk.Button(root, image=icons["STOP"], command=lambda: send_command("H"), bg="gray").grid(row=1, column=0, columnspan=2, pady=5)

root.mainloop()
