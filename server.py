from flask import Flask, request, jsonify
import sqlite3, time, os

app = Flask(__name__)
DB = "devices.db"
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS devices (
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

init_db()


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/check_device", methods=["POST"])
def check_device():
    data = request.json
    hwid = data.get("hwid")
    hostname = data.get("hostname")
    now = int(time.time())

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM devices WHERE hwid=?", (hwid,))
    row = c.fetchone()

    if not row:
        c.execute("""
            INSERT INTO devices (hwid, hostname, first_seen, last_seen, status)
            VALUES (?, ?, ?, ?, ?)
        """, (hwid, hostname, now, now, "allowed"))
        conn.commit()
        conn.close()
        return jsonify({"status": "new"}), 200

    if row["status"] == "blocked":
        conn.close()
        return jsonify({"status": "blocked"}), 403

    c.execute(
        "UPDATE devices SET last_seen=? WHERE hwid=?",
        (now, hwid)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"}), 200


@app.route("/list")
def list_devices():
    conn = get_db()
    rows = conn.execute("SELECT * FROM devices").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/block/<hwid>")
def block_device(hwid):
    conn = get_db()
    conn.execute(
        "UPDATE devices SET status='blocked' WHERE hwid=?",
        (hwid,)
    )
    conn.commit()
    conn.close()
    return "BLOCKED"


@app.route("/")
def home():
    return "Device server is running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
  
