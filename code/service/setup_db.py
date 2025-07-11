import sqlite3

conn = sqlite3.connect("api_control.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    description TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ip_requests (
    ip TEXT,
    date TEXT,
    count INTEGER,
    PRIMARY KEY (ip, date)
)
""")

# Optional: insert a token

conn.commit()
conn.close()
