import sqlite3

try:
    conn = sqlite3.connect('db/runsum.db')
    print("Database connection successful")
    conn.close()
except sqlite3.Error as e:
    print(f"Database connection failed: {e}")
