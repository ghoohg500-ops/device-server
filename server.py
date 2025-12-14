from flask import Flask, request, jsonify, render_template_string
import sqlite3, time, os

app = Flask(__name__)
DB = "devices.db"

# ===== INIT DATABASE =====
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

# ===== DB HELPER =====
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ===== API: CHECK DEVICE =====
@app.route("/check_device", methods=["POST"])
def check_device():
    data = request.get_json(force=True)   # ÉP ĐỌC JSON (QUAN TRỌNG)
    hwid = data.get("hwid")
    hostname = data.get("hostname")
    now = int(time.time())

    if not hwid:
        return jsonify({"error": "no hwid"}), 400

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

# ===== API: LIST DEVICES (JSON) =====
@app.route("/list")
def list_devices():
    conn = get_db()
    rows = conn.execute("SELECT * FROM devices ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ===== API: BLOCK DEVICE =====
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

# ===== WEB ADMIN UI =====
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Device Admin</title>
<style>
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: linear-gradient(120deg, #1e1e2f, #2b5876);
    color: #fff;
}
.container {
    max-width: 1100px;
    margin: 40px auto;
    padding: 20px;
}
h1 {
    text-align: center;
    margin-bottom: 30px;
}
.box {
    background: rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 0 20px rgba(0,0,0,0.3);
}
input {
    width: 100%;
    padding: 12px;
    border-radius: 8px;
    border: none;
    margin-top: 10px;
    font-size: 15px;
}
button {
    margin-top: 10px;
    padding: 12px 20px;
    border: none;
    border-radius: 8px;
    background: #ff4757;
    color: #fff;
    font-size: 15px;
    cursor: pointer;
}
button:hover {
    opacity: 0.85;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
}
th, td {
    padding: 10px;
    border-bottom: 1px solid rgba(255,255,255,0.2);
    text-align: center;
}
th {
    background: rgba(0,0,0,0.3);
}
.allowed { color: #2ed573; }
.blocked { color: #ff4757; }
.small { font-size: 12px; }
</style>
</head>
<body>
<div class="container">
    <h1>📊 Device Admin Panel</h1>

    <div class="box">
        <h3>🚫 Block thiết bị</h3>
        <form method="post">
            <input name="hwid" placeholder="Nhập HWID cần block">
            <button>BLOCK</button>
        </form>
    </div>

    <div class="box">
        <h3>🖥️ Danh sách thiết bị</h3>
        <table>
            <tr>
                <th>ID</th>
                <th>Hostname</th>
                <th>HWID</th>
                <th>Status</th>
                <th>Last Seen</th>
            </tr>
            {% for d in devices %}
            <tr>
                <td>{{ d.id }}</td>
                <td>{{ d.hostname }}</td>
                <td class="small">{{ d.hwid }}</td>
                <td class="{{ d.status }}">{{ d.status }}</td>
                <td>{{ d.last_seen }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>
</body>
</html>
"""

@app.route("/admin", methods=["GET", "POST"])
def admin():
    conn = get_db()
    if request.method == "POST":
        hwid = request.form.get("hwid")
        if hwid:
            conn.execute(
                "UPDATE devices SET status='blocked' WHERE hwid=?",
                (hwid,)
            )
            conn.commit()

    devices = conn.execute("SELECT * FROM devices ORDER BY id DESC").fetchall()
    conn.close()
    return render_template_string(ADMIN_HTML, devices=devices)

# ===== HOME =====
@app.route("/")
def home():
    return "Device server is running"

# ===== START =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
