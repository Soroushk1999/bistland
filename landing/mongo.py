import os
from pymongo import MongoClient


def _mongo_collection():
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
    mongo_db = os.environ.get("MONGO_DB", "landing_logs")
    client = MongoClient(mongo_uri)
    return client[mongo_db][os.environ.get("MONGO_COLLECTION", "requests")]
