from pymongo import MongoClient
import certifi

try:
    client = MongoClient(
        "mongodb+srv://AadiDes:manager@clustera.ls7ppiu.mongodb.net/?retryWrites=true&w=majority",
        tls=True,
        tlsCAFile=certifi.where()
    )
    print(client.admin.command("ping"))
except Exception as e:
    print("MongoDB connection failed:", e)
