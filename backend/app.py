import certifi
import os
from flask import request
from flask import Flask, jsonify
from pymongo import MongoClient
from flask_cors import CORS
from bson import ObjectId
from datetime import datetime, timedelta
import logging


app = Flask(__name__)
CORS(app)  # Allow all origins (you can restrict later)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AadiDes:manager@clustera.ls7ppiu.mongodb.net/?retryWrites=true&w=majority&appName=ClusterA")

try:
    client = MongoClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())
    db = client["iot_database"]
    collection = db["sensor_readings"]
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    raise

# --- Convert ObjectId and datetime to string ---
from datetime import datetime

def clean_doc(doc):
    doc["_id"] = str(doc["_id"])
    if "timestamp" in doc:
        try:
            if isinstance(doc["timestamp"], float):  # Unix time
                doc["timestamp"] = datetime.fromtimestamp(doc["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            elif hasattr(doc["timestamp"], "strftime"):
                doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        except:
            doc["timestamp"] = str(doc["timestamp"])
    return doc


# --- Routes ---
@app.route("/api/readings", methods=["GET"])
def get_all_readings():
    """Get all sensor readings with pagination."""
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))
        skip = (page - 1) * page_size
        docs = collection.find().sort("timestamp", -1).skip(skip).limit(page_size)
        logger.info(f"Fetched {collection.count_documents({})} readings (page {page})")
        return jsonify([clean_doc(doc) for doc in docs])
    except Exception as e:
        logger.error(f"Error in get_all_readings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/readings/latest/<sensor_id>", methods=["GET"])
def get_latest_reading(sensor_id):
    try:
        doc = collection.find_one({"sensor_id": sensor_id}, sort=[("timestamp", -1)])
        if doc:
            return jsonify(clean_doc(doc))
        return jsonify({"error": "Sensor not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500\

@app.route("/api/sensors", methods=["GET"])
def get_sensor_list():
    try:
        # Step 1: Fetch distinct sensor IDs with valid readings
        sensor_ids = collection.distinct("sensor_id", {
            "sensor_id": {"$nin": ["", None, "unknown", "temp", "sub"]},
            "readings": {"$exists": True, "$ne": {}}
        })

        # Step 2: Clean and filter them
        valid_ids = []
        blacklist = {"", "unknown", "temp", "sub","sensor_02","sensor_03","sensor_06","sensor0","sensor1", "null"}
        for s in sensor_ids:
            if (
                isinstance(s, str)
                and (cleaned := s.strip())
                and cleaned.lower() not in blacklist
                and cleaned.isprintable()
            ):
                valid_ids.append(cleaned)

        # Step 3: Sort and return
        return jsonify(sorted(set(valid_ids)))

    except Exception as e:
        return jsonify({"error": str(e)}), 500



def parse_date(date_str):
    """Parse YYYY-MM-DD or full timestamp into a datetime object."""
    try:
        # Try ISO format first
        return datetime.fromisoformat(date_str)
    except ValueError:
        try:
            # Try YYYY-MM-DD format
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

@app.route("/api/readings/<sensor_id>", methods=["GET"])
def get_sensor_readings(sensor_id):
    """Get readings for a specific sensor with pagination and date filtering."""
    try:
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))
        skip = (page - 1) * page_size
        query = {"sensor_id": sensor_id}
        from datetime import timezone
        min_age = datetime.now(timezone.utc) - timedelta(seconds=2)

        query["timestamp"] = {
            "$lte": min_age,
            **query.get("timestamp", {})  # merge if already exists
        }

        if start_str:
            start = parse_date(start_str)
            if start:
                query["timestamp"] = {"$gte": start}
        if end_str:
            end = parse_date(end_str)
            if end:
                if "timestamp" in query:
                    query["timestamp"]["$lte"] = end
                else:
                    query["timestamp"] = {"$lte": end}
        docs = collection.find(query).sort("timestamp", -1).skip(skip).limit(page_size)
        docs_list = list(docs)
        logger.info(f"Fetched {len(docs_list)} readings for sensor {sensor_id} (page {page})")
        return jsonify([clean_doc(doc) for doc in docs_list])
    except Exception as e:
        logger.error(f"Error in get_sensor_readings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/test", methods=["GET"])
def test_connection():
    try:
        # Test MongoDB connection
        count = collection.count_documents({})
        latest_doc = collection.find_one(sort=[("timestamp", -1)])
        
        return jsonify({
            "status": "connected",
            "total_documents": count,
            "latest_document": clean_doc(latest_doc) if latest_doc else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Run ---
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
