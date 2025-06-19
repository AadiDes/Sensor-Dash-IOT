# backend/mqtt_to_mongo.py

import os
import logging
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from datetime import datetime
from pathlib import Path

from utils_parser import parse_sensor_data
from utils_mongo import build_reading_document, mongo_insert


# Load environment
load_dotenv(dotenv_path=Path('.') / 'backend' / '.env')

# MQTT Config
BROKER = os.getenv("BROKER", "broker.emqx.io")
PORT = int(os.getenv("PORT", 1883))
TOPIC = os.getenv("TOPIC_PREFIX", "TEMP/SUB/") + "#"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mqtt_to_mongo")

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("[MQTT] Connected successfully.")
        client.subscribe(TOPIC, qos=1)
        logger.info(f"[SUBSCRIBED] {TOPIC} with QoS 1")
    else:
        logger.error(f"[MQTT] Connection failed with code {rc}")

def on_message(client, userdata, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raw_payload = msg.payload.decode()

    logging.info(f"[{timestamp}] Data on '{msg.topic}': {raw_payload}")
    readings = parse_sensor_data(raw_payload)
    print("DEBUG parsed readings:", readings)


    if not readings:
        logging.warning(f" Skipped insert due to invalid data on topic {msg.topic}")
        return

    sensor_id = msg.topic.strip().split("/")[-1] or "unknown"
    document = build_reading_document(sensor_id, readings, raw_payload, msg.topic, timestamp)

    if document:
        mongo_insert(document)
    else:
        logging.warning(f" Skipped insert due to document build failure on topic {msg.topic}")

def main():
    logger.info("Attempting MongoDB connection with config 1...")  # Already initialized in utils_mongo

    # MQTT client setup
    client = mqtt.Client(client_id="mqtt_to_mongo_subscriber")
    client.on_connect = on_connect
    client.on_message = on_message

    logger.info(f"[CONNECTING] Attempting to connect to {BROKER}:{PORT}")
    client.connect(BROKER, PORT, keepalive=60)

    logger.info("[START] MQTT loop")
    client.loop_forever()

if __name__ == "__main__":
    main()
