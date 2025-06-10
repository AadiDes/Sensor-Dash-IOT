"""mqtt_to_mongo.py

MQTT subscriber that ingests sensor readings and stores them in MongoDB Atlas
using the 'sensor_readings' schema. Master 'sensors' collection is queried
to enrich each reading with location metadata.

Environmental variables:
  - MONGODB_URI : Atlas connection string

Install dependencies:
  pip install paho-mqtt pymongo

Run:
  python mqtt_to_mongo.py
"""

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

import json
import csv
import os
import re
import sys
import logging
from datetime import datetime
import uuid
from pymongo import MongoClient, errors
import certifi

import paho.mqtt.client as mqtt
from pymongo import MongoClient, errors

# ---------------------- Configuration ---------------------- #
BROKER = "broker.emqx.io"
PORT = 1883
TOPIC = "TEMP/SUB/#"  # wildcard to catch all sensor topics

# MQTT Authentication (using public credentials for EMQX public broker)
MQTT_USERNAME = "emqx"
MQTT_PASSWORD = "public"

# Generate a unique client ID using timestamp
CLIENT_ID = f"python-mqtt-{uuid.uuid4()}"

LOG_TO_CSV = True
CSV_FILE = "sensor_log.csv"
LOG_FILE = "mqtt_client.log"
JSON_LOG_FILE = "sensor_data.json"

# Use environment variable for MongoDB URI for security
MONGO_URI = "mongodb+srv://AadiDes:manager@clustera.ls7ppiu.mongodb.net/?retryWrites=true&w=majority&appName=ClusterA"
DB_NAME = "iot_database"

if not MONGO_URI:
    logger = logging.getLogger(__name__)
    logger.error("MONGODB_URI environment variable not set. Exiting.")
    sys.exit(1)

# ---------------------- Logging Setup ---------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------- MongoDB Setup ---------------------- #
try:
    client_mongo = MongoClient(
        MONGO_URI,
        tls=True,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000
    )
    client_mongo.admin.command("ping")
    db = client_mongo[DB_NAME]
    readings_col = db["sensor_readings"]
    sensors_col = db["sensors"]
    print("✅ Connected to MongoDB")
except errors.ServerSelectionTimeoutError as e:
    print("❌ Connection failed:", e)
    exit(1)


def init_mongodb():
    """Create useful indexes if they do not already exist."""
    readings_col.create_index([("sensor_id", 1), ("timestamp", -1)], background=True)


# ---------------------- Sensor Data Parsing ---------------------- #
def parse_sensor_data(message: str) -> dict:
    """Extract numeric temperature and humidity from raw message."""
    try:
        if message.startswith("{") and message.endswith("}"):  # already JSON
            data = json.loads(message)
            return {
                "Temperature": float(data.get("T", "0").split()[0]),
                "Humidity": float(data.get("H", "0").split()[0]),
            }
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", message)
        return {
            "Temperature": float(numbers[0]) if len(numbers) > 0 else None,
            "Humidity": float(numbers[1]) if len(numbers) > 1 else None,
        }
    except Exception as exc:
        logger.warning("Error parsing sensor data: %s", exc)
        return {"Temperature": None, "Humidity": None}


def build_reading_document(topic: str, raw_message: str) -> dict:
    """Build a document for the sensor_readings collection."""
    try:
        # Parse the raw message into sensor readings
        readings = parse_sensor_data(raw_message)

        # Use system time
        system_time = datetime.now()

        # Extract sensor ID from topic, use default if not found
        sensor_id = topic.split("/")[-1] if "/" in topic else topic
        if not sensor_id:  # If sensor_id is empty
            sensor_id = "device1"  # Use default sensor ID

        # Build the document
        doc = {
            "timestamp": system_time,
            "sensor_id": sensor_id,
            "readings": {
                "temperature": {
                    "value": readings["Temperature"],
                    "unit": "C"
                },
                "humidity": {
                    "value": readings["Humidity"],
                    "unit": "%"
                }
            }
        }

        # Add location metadata if available
        sensor = sensors_col.find_one({"sensor_id": sensor_id})
        if sensor:
            doc["location"] = sensor.get("location", {})

        return doc
    except Exception as e:
        logger.error(f"Error building document: {str(e)}")
        return None


# ---------------------- MQTT Callbacks ---------------------- #

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info("[SUCCESS] Connected to %s:%s", BROKER, PORT)
        # Subscribe with QoS 1 for more reliable message delivery
        client.subscribe(TOPIC, qos=1)
        logger.info("[SUBSCRIBED] %s with QoS 1", TOPIC)
    else:
        logger.error("[ERROR] Connection failed with code %s - %s", rc, mqtt.error_string(rc))


def on_message(client, userdata, msg):
    # Use system time
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raw_message = msg.payload.decode()
    logger.info("[%s] Data on '%s': %s", timestamp, msg.topic, raw_message)

    # ---------------------- MongoDB insert ---------------------- #
    doc = build_reading_document(msg.topic, raw_message)
    if doc:
        try:
            readings_col.insert_one(doc)
            logger.debug("[MongoDB] Inserted reading for %s", doc["sensor_id"])
        except Exception as exc:
            logger.error("[MongoDB] Insert failed: %s", exc)

    # ---------------------- Optional local logs ---------------------- #
    try:
        if not os.path.exists(JSON_LOG_FILE):
            with open(JSON_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        try:
            with open(JSON_LOG_FILE, "r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []
        except IOError as exc:
            logger.error("Error reading JSON log: %s", exc)
            existing = []

        # Convert datetime to string for JSON
        doc_for_json = doc.copy()
        doc_for_json["timestamp"] = timestamp
        existing.append(doc_for_json)

        with open(JSON_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, default=str, indent=2)

    except IOError as exc:
        logger.error("Error writing JSON log: %s", exc)

    if LOG_TO_CSV:
        try:
            if not os.path.exists(CSV_FILE):
                with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(["Timestamp", "Topic", "Temp", "Hum"])
            with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    timestamp,
                    msg.topic,
                    doc["readings"].get("temperature", {}).get("value", "N/A"),
                    doc["readings"].get("humidity", {}).get("value", "N/A"),
                ])
        except IOError as exc:
            logger.error("Error writing CSV: %s", exc)



def on_disconnect(client, userdata, rc, properties=None):
    if rc != 0:
        logger.warning(f"[DISCONNECTED] Unexpected disconnection. Reason code: {rc} - {mqtt.error_string(rc)}")
        # Don't try to reconnect here - let the client handle it automatically
    else:
        logger.info("[DISCONNECTED] Normal disconnection")


# ---------------------- Main ---------------------- #

def main():
    init_mongodb()
    # Use MQTT v3.1.1 instead of v5 for better compatibility
    client = mqtt.Client(client_id="AadiDes", protocol=mqtt.MQTTv311, clean_session=True)

    # Set authentication credentials
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    # Enable automatic reconnect with more conservative settings
    client.enable_logger(logger)
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    # Set maximum number of queued messages
    client.max_inflight_messages_set(10)

    # Connect to the broker with increased keepalive and connection timeout
    try:
        logger.info("[CONNECTING] Attempting to connect to %s:%s", BROKER, PORT)
        # Add connection timeout and retry settings
        client.connect(BROKER, PORT, keepalive=120, bind_address="")
        logger.info("[START] MQTT loop")
        client.loop_forever()
    except Exception as e:
        logger.error("[ERROR] Connection failed: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()