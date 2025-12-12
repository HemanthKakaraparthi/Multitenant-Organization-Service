from pymongo import MongoClient

uri = "YOUR_MONGO_URI_HERE"

try:
    client = MongoClient(uri)
    print("Connected!")
    print("Databases:", client.list_database_names())
except Exception as e:
    print("ERROR:", e)
