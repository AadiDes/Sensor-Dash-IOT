import os
import json
import time
import random
import threading
import argparse
import logging
import sys
import dateutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from dateutil.parser import parse as parse_dt

# Load environment variables
load_dotenv(dotenv_path=Path('.') / 'backend' / '.env')
BROKER = os.getenv("BROKER", "broker.emqx.io")
PORT = int(os.getenv("PORT", 1883))
TOPIC_PREFIX = os.getenv("TOPIC_PREFIX", "TEMP/SUB/")
SIM_INTERVAL = int(os.getenv("SIM_INTERVAL", 10))
LOG_FILE = os.getenv("LOG_FILE", "mqtt_manager.log")

# Logging setup (no emojis, utf-8 safe)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# ========== Base MQTT Class ==========
class MqttBase:
    def __init__(self, client_id=None):
        self.client = mqtt.Client(client_id=client_id, userdata=None, protocol=mqtt.MQTTv311)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.connected = False

    def connect(self):
        logging.info(f"[MQTT] Connecting to {BROKER}:{PORT}")
        self.client.connect(BROKER, PORT, 60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        self.connected = True
        if rc == 0:
            logging.info("[MQTT] Connected successfully.")
        else:
            logging.error(f"[MQTT] Connection failed with code {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        logging.warning("[MQTT] Disconnected.")


# ========== Simulator ==========
class MqttSimulator(MqttBase):
    def __init__(self, sensor_id="simdevice"):
        super().__init__(client_id=f"sim-{sensor_id}")
        self.sensor_id = sensor_id
        self.topic = f"{TOPIC_PREFIX}{self.sensor_id}"

    def generate_payload(self):
        return {
            "T": f"{random.uniform(20.0, 35.0):.2f} C",
            "H": f"{random.uniform(30.0, 70.0):.2f} %",
            "date time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def run(self):
        self.connect()
        logging.info(f"Simulator started for sensor: {self.sensor_id} every {SIM_INTERVAL}s")
        try:
            while True:
                payload = self.generate_payload()
                self.client.publish(self.topic, json.dumps(payload), qos=1)
                logging.info(f"[PUBLISH] {self.topic} → {payload}")
                time.sleep(SIM_INTERVAL)
        except KeyboardInterrupt:
            self.disconnect()
            logging.info("[SIMULATOR] Stopped.")


# ========== Subscriber ==========
class MqttSubscriber(MqttBase):
    def __init__(self, topic_filter=f"{TOPIC_PREFIX}#"):
        super().__init__(client_id="subscriber")
        self.topic_filter = topic_filter

    def on_message(self, client, userdata, msg):
        from utils_parser import parse_sensor_data
        from utils_mongo import build_reading_document, mongo_insert
        if msg.topic.strip().count("/") < 2:
            logging.warning(f" Ignoring message on incomplete topic '{msg.topic}'")
            return

        raw_payload = msg.payload.decode()
        received_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"[RECEIVED] {msg.topic}: {raw_payload}")

        try:
            payload = json.loads(raw_payload)
        except Exception as e:
            logging.warning(f"[ERROR] Invalid JSON: {e}")
            return

        readings = parse_sensor_data(raw_payload)
        if readings is None:
            logging.warning(f"[WARNING] Skipped insert: Could not parse sensor data from topic {msg.topic}")
            return

        sensor_id = msg.topic.strip().split("/")[-1] or "unknown"
        payload_ts = payload.get("date time") or payload.get("datetime") or payload.get("timestamp")

        try:
            sensor_ts = parse_dt(payload_ts) if payload_ts else datetime.now()
        except Exception:
            sensor_ts = received_at

        document = build_reading_document(sensor_id, readings, raw_payload, msg.topic, sensor_ts)
        if document:
            mongo_insert(document)
        else:
            logging.warning(f"[WARNING] Skipped insert: Invalid document for topic {msg.topic}")

    def run(self):
        self.client.on_message = self.on_message
        self.connect()
        self.client.subscribe(self.topic_filter)
        logging.info(f"Subscribed to topic filter: {self.topic_filter}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.disconnect()
            logging.info("[SUBSCRIBER] Stopped.")


# ========== Main ==========
def main():
    parser = argparse.ArgumentParser(description="MQTT Manager")
    parser.add_argument("--simulate", action="store_true", help="Run simulator")
    parser.add_argument("--subscribe", action="store_true", help="Run subscriber")
    parser.add_argument("--sensor-id", type=str, default="simdevice", help="Sensor ID for simulator")
    args = parser.parse_args()

    threads = []

    if args.simulate:
        sim = MqttSimulator(sensor_id=args.sensor_id)
        t1 = threading.Thread(target=sim.run)
        threads.append(t1)
        t1.start()

    if args.subscribe:
        sub = MqttSubscriber()
        t2 = threading.Thread(target=sub.run)
        threads.append(t2)
        t2.start()

    if not (args.simulate or args.subscribe):
        print("❌ Please use --simulate, --subscribe, or both.")
        return

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
