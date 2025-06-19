# simulate_sensor.py
import time
import json
import random
import paho.mqtt.client as mqtt

BROKER = "broker.emqx.io"
PORT = 1883  # use 8083 for WebSocket (only if needed)
TOPIC = "temp/simdevice"  # simulated sensor topic
INTERVAL = 20  # seconds between messages

def generate_payload():
    return {    
        "temperature": round(random.uniform(20.0, 30.0), 2),
        "humidity": round(random.uniform(40.0, 60.0), 2)
    }

def main():
    client = mqtt.Client()
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    print(f"🔌 Connected. Publishing to {TOPIC} every {INTERVAL} seconds...")

    try:
        while True:
            payload = generate_payload()
            msg = json.dumps(payload)
            client.publish(TOPIC, msg, qos=1, retain=False)
            print(f"{TOPIC} → {msg}")
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("Stopped.")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
