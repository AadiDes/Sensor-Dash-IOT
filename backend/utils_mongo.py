# backend/utils_mongo.py
import json
import os
import logging
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient, ASCENDING, DESCENDING


logger = logging.getLogger(__name__)

# Load MongoDB credentials
load_dotenv(dotenv_path=Path('.') / 'backend' / '.env')
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGO_DB", "iot_database")
COLLECTION = os.getenv("MONGO_COLLECTION", "sensor_readings")

# MongoDB Setup
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION]

# Ensure indexes
collection.create_index([("sensor_id", ASCENDING), ("timestamp", DESCENDING)])

from datetime import datetime

# backend/utils_mongo.py

def build_reading_document(sensor_id: str, readings: dict, raw_message: str, topic: str, received_at: str) -> dict | None:
    from datetime import datetime

    if not sensor_id or not readings:
        return None

    sensor_id = sensor_id.strip()
    if not sensor_id.isalnum() or sensor_id.lower() in ["", "temp", "sub", "unknown"]:
        logger.warning(f"Invalid or generic sensor_id '{sensor_id}' from topic '{topic}'. Skipping.")
        return None

    if not any(isinstance(v, str) and any(char.isdigit() for char in v) for v in readings.values()):
        logger.warning(f"Invalid reading: {readings}, topic={topic}, message={raw_message}")
        return None

    # Try to extract timestamp from "date time" field in payload
    try:
        parsed_payload = json.loads(raw_message)
        timestamp_str = parsed_payload.get("date time")
        timestamp_dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        timestamp_dt = datetime.now()

    return {
        "sensor_id": sensor_id,
        "readings": readings,
        "topic": topic,
        "timestamp": timestamp_dt,
        "raw": raw_message,
    }




def mongo_insert(doc: dict) -> None:
    """Insert document into MongoDB."""
    try:
        collection.insert_one(doc)
        logger.info(f"✅ Inserted document for sensor_id: {doc['sensor_id']}")
    except Exception as e:
        logger.error(f"Mongo insert failed: {e}")
