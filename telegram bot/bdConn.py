import os
import psycopg2 # type: ignore
from dotenv import load_dotenv # type: ignore

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn