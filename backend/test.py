# migrate_shubh.py
from pymongo import MongoClient
import os

uri = os.getenv("MONGODB_URI")
client = MongoClient(uri)

# From wrong DB
src = client["iot_dashboard"]["sensor_readings"]

# To correct DB
dest = client["iot_database"]["sensor_readings"]

docs = list(src.find({"sensor_id": "Shubh"}))
if docs:
    dest.insert_many(docs)
    print(f"✅ Migrated {len(docs)} documents for 'Shubh'")
else:
    print("❌ No documents found for 'Shubh'")
