from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
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
<h1>Device Admin</h1>
<a href="/logout">🚪 Logout</a>
<form method="post">
<input name="block_hwid" placeholder="HWID block">
<button>BLOCK</button>
</form>
<form method="post">
<input name="unblock_hwid" placeholder="HWID unblock">
<button>UNBLOCK</button>
</form>
<table border=1>
<tr><th>ID</th><th>Hostname</th><th>HWID</th><th>Status</th><th>Action</th></tr>
{% for d in devices %}
<tr>
<td>{{ d.id }}</td>
<td>{{ d.hostname }}</td>
<td>{{ d.hwid }}</td>
<td>{{ d.status }}</td>
<td><a href="/delete_device/{{ d.id }}">❌ Delete</a></td>
</tr>
{% endfor %}
</table>
"""

@app.route("/")
def home():
    return "Device server is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
