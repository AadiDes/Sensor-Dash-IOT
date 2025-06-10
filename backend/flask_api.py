import certifi
import os
from flask import request
from flask import Flask, jsonify
from pymongo import MongoClient
from flask_cors import CORS
from bson import ObjectId
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow all origins (you can restrict later)

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
def clean_doc(doc):
    doc["_id"] = str(doc["_id"])
    if "timestamp" in doc:
        doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return doc

# --- Routes ---
@app.route("/api/readings", methods=["GET"])
def get_all_readings():
    try:
        docs = collection.find().sort("timestamp", -1).limit(100)
        return jsonify([clean_doc(doc) for doc in docs])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/readings/latest/<sensor_id>", methods=["GET"])
def get_latest_reading(sensor_id):
    try:
        doc = collection.find_one({"sensor_id": sensor_id}, sort=[("timestamp", -1)])
        if doc:
            return jsonify(clean_doc(doc))
        return jsonify({"error": "Sensor not found"}), 404
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
    try:
        # 🔎 Read date filters from query params
        start_str = request.args.get("start")
        end_str = request.args.get("end")

        query = {"sensor_id": sensor_id}

        # ⏱ Build date filter
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

        docs = collection.find(query).sort("timestamp", -1).limit(100)
        return jsonify([clean_doc(doc) for doc in docs])
    except Exception as e:
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
