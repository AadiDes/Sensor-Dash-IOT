from pymongo import MongoClient
import certifi

MONGO_URI = "mongodb+srv://AadiDes:manager@clustera.ls7ppiu.mongodb.net/?retryWrites=true&w=majority&appName=ClusterA"
client = MongoClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())
db = client["iot_database"]
collection = db["sensor_readings"]

result = collection.update_many(
    {"sensor_id": ""},
    {"$set": {"sensor_id": "device1"}}
)
print(f"Updated {result.modified_count} documents.")