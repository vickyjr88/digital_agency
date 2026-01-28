
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT typname FROM pg_type WHERE typname = 'verificationstatus'")
    result = cur.fetchone()
    if result:
        print(f"Type exists: {result[0]}")
    else:
        print("Type does not exist")
    cur.close()
    conn.close()
except Exception as e:
    print(e)
