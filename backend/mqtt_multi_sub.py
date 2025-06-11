
# backend/mqtt_multi_sub.py

import json, signal, threading, time
from collections import defaultdict
from pymongo import MongoClient
import paho.mqtt.client as mqtt

# CONFIG
MONGO_URI = "mongodb+srv://AadiDes:manager@clustera.ls7ppiu.mongodb.net/?retryWrites=true&w=majority&appName=ClusterA"
DATABASE = "myproject"
REFRESH_SECS = 60  # refresh the subscriptions every 60 seconds

mongo = MongoClient(MONGO_URI)[DATABASE]
stop_event = threading.Event()
connections = {}            # broker_url -> mqtt.Client
topics_cache = defaultdict(set)


def fetch_subscriptions():
    subs = list(mongo.subscriptions.find({"enabled": True}))
    mapping = defaultdict(set)
    for s in subs:
        mapping[s["broker_url"]].add(s["topic_pattern"])
    return mapping


def start_client(broker, topics, cred):
    client = mqtt.Client()
    if cred.get("username"):
        client.username_pw_set(cred["username"], cred.get("password", ""))

    def on_connect(cl, *_):
        print(f"[{broker}] connected")
        for t in topics:
            cl.subscribe(t)
            print(f"Subscribed to {t}")

    def on_message(cl, _, msg):
        payload = msg.payload.decode()
        try:
            data = json.loads(payload)
        except:
            data = {"value": payload}

        topic_parts = msg.topic.split("/")
        device_id = topic_parts[1] if len(topic_parts) > 1 else "unknown"

        doc = {
            "timestamp": time.time(),
            "topic": msg.topic,
            "sensor_id": device_id,
            "broker": broker,
            "readings": data
        }
        mongo.sensor_readings.insert_one(doc)
        print(f"[{broker}] {msg.topic} -> {data}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(broker)
    client.loop_start()
    return client


def supervisor():
    global topics_cache, connections
    while not stop_event.is_set():
        latest = fetch_subscriptions()

        for broker, topics in latest.items():
            cred = mongo.subscriptions.find_one({"broker_url": broker}, {"username": 1, "password": 1})
            if broker not in connections:
                connections[broker] = start_client(broker, topics, cred or {})
            else:
                extra = topics - topics_cache[broker]
                for t in extra:
                    connections[broker].subscribe(t)

        # remove old brokers
        for broker in set(topics_cache) - set(latest):
            connections[broker].loop_stop()
            connections[broker].disconnect()
            del connections[broker]

        topics_cache = latest
        stop_event.wait(REFRESH_SECS)


if __name__ == "__main__":
    t = threading.Thread(target=supervisor, daemon=True)
    t.start()
    print("Multi-topic MQTT subscriber is running. Press Ctrl+C to stop.")
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()

