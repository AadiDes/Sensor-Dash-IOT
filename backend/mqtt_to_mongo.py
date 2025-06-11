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
import time
import ssl

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
def connect_to_mongodb():
    """Connect to MongoDB with multiple fallback options for SSL issues"""

    # Try different connection configurations
    connection_configs = [
        # Config 1: Standard SSL with certifi
        {
            "tls": True,
            "tlsCAFile": certifi.where(),
            "serverSelectionTimeoutMS": 10000,
            "connectTimeoutMS": 10000,
            "socketTimeoutMS": 10000,
        },
        # Config 2: SSL with insecure flag (not recommended for production)
        {
            "tls": True,
            "tlsAllowInvalidCertificates": True,
            "tlsAllowInvalidHostnames": True,
            "serverSelectionTimeoutMS": 10000,
            "connectTimeoutMS": 10000,
            "socketTimeoutMS": 10000,
        },
        # Config 3: Disable SSL certificate verification
        {
            "tls": True,
            "tlsInsecure": True,
            "serverSelectionTimeoutMS": 10000,
            "connectTimeoutMS": 10000,
            "socketTimeoutMS": 10000,
        },
        # Config 4: Manual SSL context
        {
            "tls": True,
            "tlsCAFile": None,
            "ssl_cert_reqs": ssl.CERT_NONE,
            "serverSelectionTimeoutMS": 10000,
            "connectTimeoutMS": 10000,
            "socketTimeoutMS": 10000,
        }
    ]

    for i, config in enumerate(connection_configs, 1):
        try:
            logger.info(f"Attempting MongoDB connection with config {i}...")
            client_mongo = MongoClient(MONGO_URI, **config)

            # Test the connection
            client_mongo.admin.command("ping")
            logger.info(f"✅ Successfully connected to MongoDB using config {i}")
            return client_mongo

        except Exception as e:
            logger.warning(f"Config {i} failed: {str(e)}")
            if i < len(connection_configs):
                logger.info(f"Trying next configuration...")
            continue

    # If all configs fail, raise the last exception
    raise Exception("All MongoDB connection attempts failed")


try:
    client_mongo = connect_to_mongodb()
    db = client_mongo[DB_NAME]
    readings_col = db["sensor_readings"]
    sensors_col = db["sensors"]
    logger.info("✅ MongoDB connection established successfully")
except Exception as e:
    logger.error(f"❌ Failed to connect to MongoDB: {e}")
    sys.exit(1)


def init_mongodb():
    """Create useful indexes if they do not already exist."""
    try:
        readings_col.create_index([("sensor_id", 1), ("timestamp", -1)], background=True)
        logger.info("✅ MongoDB indexes created/verified")
    except Exception as e:
        logger.warning(f"Index creation failed: {e}")


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


def safe_insert(doc, retries=3, delay=2):
    """Insert a document into MongoDB with retry logic."""
    for attempt in range(retries):
        try:
            readings_col.insert_one(doc)
            logger.info(f"[MongoDB] Inserted reading for {doc.get('sensor_id', 'unknown')}")
            return True
        except Exception as exc:
            logger.error(f"[MongoDB] Insert failed (attempt {attempt + 1}): {exc}")
            if attempt < retries - 1:
                time.sleep(delay)
    logger.error("[MongoDB] All insert attempts failed.")
    return False


def build_reading_document(topic: str, raw_message: str) -> dict:
    """Build a document for the sensor_readings collection. Validates and sanitizes data."""
    try:
        readings = parse_sensor_data(raw_message)
        system_time = datetime.now()
        sensor_id = topic.split("/")[-1] if "/" in topic else topic
        if not sensor_id or not isinstance(sensor_id, str):
            sensor_id = "device1"
        # Validate readings
        temp = readings["Temperature"]
        hum = readings["Humidity"]
        if temp is None or hum is None:
            logger.warning(f"Invalid reading: temp={temp}, hum={hum}, topic={topic}, message={raw_message}")
            return None
        doc = {
            "timestamp": system_time,
            "sensor_id": sensor_id.strip(),
            "readings": {
                "temperature": {"value": temp, "unit": "C"},
                "humidity": {"value": hum, "unit": "%"}
            }
        }
        try:
            sensor = sensors_col.find_one({"sensor_id": sensor_id})
            if sensor:
                doc["location"] = sensor.get("location", {})
        except Exception as e:
            logger.warning(f"Could not fetch sensor metadata: {e}")
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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raw_message = msg.payload.decode()
    logger.info(f"[{timestamp}] Data on '{msg.topic}': {raw_message}")
    doc = build_reading_document(msg.topic, raw_message)
    if doc:
        safe_insert(doc)

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
    try:
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
        logger.info("[CONNECTING] Attempting to connect to %s:%s", BROKER, PORT)
        # Add connection timeout and retry settings
        client.connect(BROKER, PORT, keepalive=120, bind_address="")
        logger.info("[START] MQTT loop")
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error("[ERROR] Application failed: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()