
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT to_regclass('wallets')")
    result = cur.fetchone()
    if result and result[0]:
        print("Table 'wallets' exists")
    else:
        print("Table 'wallets' does NOT exist")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
