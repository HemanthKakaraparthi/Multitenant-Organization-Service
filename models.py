from pymongo import MongoClient
from config import MONGO_URI, MASTER_DB


client = MongoClient(MONGO_URI)
master_db = client[MASTER_DB]


# Collections in master DB
organizations_col = master_db['organizations']
admins_col = master_db['admins']


# Helper to get per-org collection name


def org_collection_name(org_name: str) -> str:
# sanitize name: lower, replace spaces with underscores
    safe = org_name.strip().lower().replace(' ', '_')
    return f"org_{safe}"


# Create per-org collection (no-op if exists)


def ensure_org_collection(name: str):
    cname = org_collection_name(name)
    if cname not in master_db.list_collection_names():
        master_db.create_collection(cname)
    return master_db[cname]


# Drop per-org collection


def drop_org_collection(name: str):
    cname = org_collection_name(name)
    if cname in master_db.list_collection_names():
        master_db.drop_collection(cname)
        return True
    return False