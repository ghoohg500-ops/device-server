import sqlite3

conn = sqlite3.connect("devices.db")
c = conn.cursor()

c.execute("""
CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hwid TEXT UNIQUE,
    hostname TEXT,
    first_seen INTEGER,
    last_seen INTEGER,
    status TEXT
)
""")

conn.commit()
conn.close()
print("DB created")
