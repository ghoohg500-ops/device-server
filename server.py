from flask import Flask, request, jsonify, render_template_string, redirect, session
import sqlite3, time, os

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"
DB = "devices.db"

# ===== ADMIN LOGIN CONFIG =====
ADMIN_USER = "hoangnam0303"
ADMIN_PASS = "nam0303"

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

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ===== API CHECK DEVICE =====
@app.route("/check_device", methods=["POST"])
def check_device():
    data = request.get_json(force=True)
    hwid = data.get("hwid")
    hostname = data.get("hostname", "unknown")
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

    c.execute("UPDATE devices SET last_seen=? WHERE hwid=?", (now, hwid))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"}), 200

# ===== LOGIN PAGE =====
LOGIN_HTML = """
<!doctype html>
<html>
<head>
<title>Admin Login</title>
<style>
body {
    background: linear-gradient(120deg,#1e1e2f,#2b5876);
    font-family: Arial;
    color: white;
}
.box {
    width: 320px;
    margin: 120px auto;
    background: rgba(255,255,255,0.1);
    padding: 25px;
    border-radius: 12px;
    box-shadow: 0 0 20px rgba(0,0,0,0.4);
}
input, button {
    width: 100%;
    padding: 12px;
    margin-top: 10px;
    border-radius: 8px;
    border: none;
}
button {
    background: #2ed573;
    font-size: 15px;
}
.error { color: #ff6b6b; }
</style>
</head>
<body>
<div class="box">
<h2>🔐 Admin Login</h2>
<form method="post">
<input name="username" placeholder="Username">
<input name="password" type="password" placeholder="Password">
<button>LOGIN</button>
</form>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
</div>
</body>
</html>
"""

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if (request.form["username"] == ADMIN_USER and
            request.form["password"] == ADMIN_PASS):
            session["admin"] = True
            return redirect("/admin")
        else:
            error = "Sai tài khoản hoặc mật khẩu"
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")

# ===== DELETE DEVICE =====
@app.route("/delete_device/<int:device_id>")
def delete_device(device_id):
    if not session.get("admin"):
        return redirect("/login")
    conn = get_db()
    conn.execute("DELETE FROM devices WHERE id=?", (device_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")

# ===== ADMIN PANEL =====
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin"):
        return redirect("/login")

    conn = get_db()

    if request.method == "POST":
        if request.form.get("block_hwid"):
            conn.execute(
                "UPDATE devices SET status='blocked' WHERE hwid=?",
                (request.form["block_hwid"],)
            )
        if request.form.get("unblock_hwid"):
            conn.execute(
                "UPDATE devices SET status='allowed' WHERE hwid=?",
                (request.form["unblock_hwid"],)
            )
        conn.commit()

    devices = conn.execute("SELECT * FROM devices ORDER BY id DESC").fetchall()
    conn.close()

    return render_template_string(ADMIN_HTML, devices=devices)

# ===== ADMIN HTML =====
ADMIN_HTML = """
<!doctype html>
<html>
<head>
<title>Device Admin Panel</title>
<style>
body {
    margin: 0;
    font-family: Arial;
    background: linear-gradient(120deg,#1e1e2f,#2b5876);
    color: #fff;
}
.header {
    padding: 20px;
    font-size: 22px;
    background: rgba(0,0,0,0.25);
}
.container {
    width: 95%;
    max-width: 1000px;
    margin: 30px auto;
}
.card {
    background: rgba(255,255,255,0.08);
    padding: 20px;
    border-radius: 14px;
    margin-bottom: 20px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}
input {
    width: 100%;
    padding: 12px;
    border-radius: 8px;
    border: none;
    margin-bottom: 10px;
}
button {
    padding: 10px 18px;
    border: none;
    border-radius: 8px;
    font-weight: bold;
}
.block-btn { background: #ff4757; color: white; }
.unblock-btn { background: #2ed573; color: white; }
.logout {
    float: right;
    color: #ff6b6b;
    text-decoration: none;
}
table {
    width: 100%;
    border-collapse: collapse;
}
th, td {
    padding: 10px;
    border-bottom: 1px solid rgba(255,255,255,0.2);
}
.status-ok { color: #2ed573; font-weight: bold; }
.status-block { color: #ff6b6b; font-weight: bold; }
.delete { color: #ff6b6b; text-decoration: none; }
</style>
</head>

<body>

<div class="header">
📊 Device Admin Panel
<a class="logout" href="/logout">🚪 Logout</a>
</div>

<div class="container">

<div class="card">
<h3>🚫 Block thiết bị</h3>
<form method="post">
<input name="block_hwid" placeholder="Nhập HWID cần block">
<button class="block-btn">BLOCK</button>
</form>
</div>

<div class="card">
<h3>✅ Gỡ block thiết bị</h3>
<form method="post">
<input name="unblock_hwid" placeholder="Nhập HWID cần unblock">
<button class="unblock-btn">UNBLOCK</button>
</form>
</div>

<div class="card">
<h3>📋 Danh sách thiết bị</h3>
<table>
<tr>
<th>ID</th>
<th>Hostname</th>
<th>HWID</th>
<th>Status</th>
<th>Action</th>
</tr>
{% for d in devices %}
<tr>
<td>{{ d.id }}</td>
<td>{{ d.hostname }}</td>
<td style="font-size:12px">{{ d.hwid }}</td>
<td class="{{ 'status-block' if d.status == 'blocked' else 'status-ok' }}">
{{ d.status }}
</td>
<td>
<a class="delete" href="/delete_device/{{ d.id }}">❌ Delete</a>
</td>
</tr>
{% endfor %}
</table>
</div>

</div>
</body>
</html>
"""

@app.route("/")
def home():
    return "Device server is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
