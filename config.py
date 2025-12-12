import os
from dotenv import load_dotenv
from datetime import timedelta


load_dotenv()


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MASTER_DB = os.getenv("MASTER_DB", "multitenant_master")
JWT_SECRET = os.getenv("JWT_SECRET", "change_this_secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "86400"))
FLASK_SECRET_KEY = os.getenv("SECRET_KEY", "flask_secret")