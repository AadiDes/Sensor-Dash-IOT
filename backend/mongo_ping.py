from pymongo import MongoClient
import certifi
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

try:
    client = MongoClient(
        os.environ.get("MONGODB_URI"),
        tlsCAFile=certifi.where()
    )

    print(client.admin.command("ping"))
except Exception as e:
    print("MongoDB connection failed:", e)
