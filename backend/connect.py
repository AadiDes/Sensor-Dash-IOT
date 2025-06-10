import json
import csv
import paho.mqtt.client as mqtt
from datetime import datetime

# ---------------------- Configuration ---------------------- #
BROKER = "broker.emqx.io"
PORT = 1883
LOG_TO_CSV = True
TOPIC = "TEMP/SUB/"
CSV_FILE = "sensor_log.csv"
# ----------------------------------------------------------- #

# ----------------- MQTT v5 Callback API ------------------ #
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"✅ Connected to broker at {BROKER}:{PORT}")
        client.subscribe(TOPIC)
        print(f"📡 Subscribed to topic: {TOPIC}")
    else:
        print(f"❌ Failed to connect. Reason code: {reason_code}")

# Callback when a message is received
def on_message(client, userdata, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        payload = json.loads(msg.payload.decode())
        value = payload.get("value", "N/A")
        unit = payload.get("unit", "")
        device = payload.get("device_id", "unknown")
        print(f"[{timestamp}] 🔎 {device}: {value} {unit} (Topic: {msg.topic})")

        if LOG_TO_CSV:
            with open(CSV_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, msg.topic, device, value, unit])

    except json.JSONDecodeError:
        # Raw message fallback
        raw = msg.payload.decode()
        print(f"[{timestamp}] 📥 Raw message on '{msg.topic}': {raw}")

        if LOG_TO_CSV:
            with open(CSV_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, msg.topic, "raw", raw, ""])

# Callback when disconnected
def on_disconnect(client, userdata, reason_code, properties):
    print("🔌 Disconnected from broker.")
    try:
        client.reconnect()
        print("🔁 Reconnecting...")
    except Exception as e:
        print("⚠️ Reconnect failed:", str(e))

# -------------- Initialize and Run MQTT Client ------------- #
client = mqtt.Client(client_id="AadiDes", protocol=mqtt.MQTTv5)

client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

client.connect(BROKER, PORT, keepalive=60)
client.loop_forever()
