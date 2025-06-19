# backend/mqtt_multi_sub.py

from datetime import datetime
import json, signal, threading, time
from collections import defaultdict
from pymongo import MongoClient
import paho.mqtt.client as mqtt
import certifi
import urllib.parse
import logging
import os

# -------------------- CONFIG -------------------- #
MONGO_URI = "mongodb+srv://AadiDes:manager@clustera.ls7ppiu.mongodb.net/?retryWrites=true&w=majority&appName=ClusterA"
DATABASE = "iot_database"
REFRESH_SECS = 60  # Subscription refresh interval in seconds
LOG_FILE = "mqtt_multi_sub.log"

# ------------------ Logging Setup ------------------ #
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),               # Console output
        logging.FileHandler(LOG_FILE)          # Log to file
    ]
)

# ------------------ MongoDB Setup ------------------ #
mongo = MongoClient(MONGO_URI, tlsCAFile=certifi.where())[DATABASE]

# ------------------ Globals ------------------ #
stop_event = threading.Event()
connections = {}                      # broker_url -> mqtt.Client
topics_cache = defaultdict(set)


def fetch_subscriptions():
    """Fetch active broker-topic mappings from MongoDB."""
    subs = list(mongo.subscriptions.find({"enabled": True}))
    mapping = defaultdict(set)
    for s in subs:
        mapping[s["broker_url"]].add(s["topic_pattern"])
    return mapping


def start_client(broker, topics, cred):
    """Start a new MQTT client with given broker and topics."""
    client = mqtt.Client(transport="websockets")

    if cred.get("username"):
        client.username_pw_set(cred["username"], cred.get("password", ""))

    def on_connect(cl, userdata, flags, rc):
        if rc == 0:
            logging.info(f"[{broker}] ✅ CONNECTED")
            for t in topics:
                cl.subscribe(t)
                logging.info(f"[{broker}] 🔗 Subscribed to {t}")
        else:
            logging.warning(f"[{broker}] ❌ Connect failed with code {rc}")

    def on_message(cl, _, msg):
        payload = msg.payload.decode()
        try:
            data = json.loads(payload)
        except:
            data = {"value": payload}

        if msg.topic == "temp":
            return  # Skip irrelevant topic

        topic_parts = msg.topic.split("/")
        device_id = topic_parts[1] if len(topic_parts) > 1 else "unknown"

        doc = {
            "timestamp": datetime.utcnow(),
            "topic": msg.topic,
            "sensor_id": device_id,
            "broker": broker,
            "readings": data
        }

        try:
            result = mongo.sensor_readings.insert_one(doc)
            logging.info(f"[{broker}] {msg.topic} → {data} (Inserted: {result.acknowledged})")
        except Exception as e:
            logging.error(f"🚨 Failed to insert document: {e}")

    # Attach callbacks
    client.on_connect = on_connect
    client.on_message = on_message

    # Parse and connect to broker
    parsed = urllib.parse.urlparse(broker)
    host = parsed.hostname
    port = parsed.port

    try:
        client.connect_async(host, port=port)
        client.loop_start()
        return client
    except Exception as e:
        logging.error(f"❌ Could not connect to {broker}: {e}")
        return None


def supervisor():
    """Continuously refresh subscriptions and maintain broker connections."""
    global topics_cache, connections
    while not stop_event.is_set():
        try:
            latest = fetch_subscriptions()
            logging.info(f"📥 Fetched {len(latest)} broker(s) from MongoDB")
        except Exception as e:
            logging.error(f"🚨 Error fetching subscriptions: {e}")
            time.sleep(10)
            continue

        for broker, topics in latest.items():
            logging.info(f" → {broker}: {list(topics)}")
            cred = mongo.subscriptions.find_one({"broker_url": broker}, {"username": 1, "password": 1})

            if broker not in connections:
                connections[broker] = start_client(broker, topics, cred or {})
            else:
                extra = topics - topics_cache[broker]
                for t in extra:
                    connections[broker].subscribe(t)
                    logging.info(f"[{broker}] ➕ Subscribed to new topic: {t}")

        # Disconnect from removed brokers
        for broker in set(topics_cache) - set(latest):
            connections[broker].loop_stop()
            connections[broker].disconnect()
            del connections[broker]
            logging.info(f"[{broker}] 🔌 Disconnected (removed from subscriptions)")

        topics_cache = latest
        stop_event.wait(REFRESH_SECS)


if __name__ == "__main__":
    t = threading.Thread(target=supervisor, daemon=True)
    t.start()
    print("📡 Multi-topic MQTT subscriber is running. Press Ctrl+C to stop.")
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        print("🛑 Exiting on user interrupt...")
