from flask import Flask, request, redirect, render_template, jsonify
import sqlite3
from hashids import Hashids
import os

app = Flask(__name__)
DB_NAME = os.path.join(os.path.dirname(__file__), "database.db")


# Hashids setup (salt makes it non-predictable)
hashids = Hashids(salt="mini-bitly-secret-key", min_length=6)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS urls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        long_url TEXT NOT NULL,
        short_code TEXT UNIQUE NOT NULL,
        clicks INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_short_code ON urls(short_code)
    """)
    conn.commit()
    conn.close()

init_db()  # run on startup


# ------------------ DB Connection ------------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ------------------ Home Page (UI) ------------------
@app.route("/", methods=["GET", "POST"])
def index():
    short_url = None

    if request.method == "POST":
        long_url = request.form["long_url"]
        conn = get_db()
        cur = conn.cursor()

        # Check if already exists
        cur.execute("SELECT short_code FROM urls WHERE long_url=?", (long_url,))
        row = cur.fetchone()

        if row:
            code = row["short_code"]
        else:
            cur.execute("INSERT INTO urls (long_url, short_code, clicks) VALUES (?, ?, ?)",
                        (long_url, "temp", 0))
            conn.commit()

            url_id = cur.lastrowid
            code = hashids.encode(url_id)

            cur.execute("UPDATE urls SET short_code=? WHERE id=?", (code, url_id))
            conn.commit()

        conn.close()
        short_url = request.host_url + code

    return render_template("index.html", short_url=short_url)

# ------------------ Redirect & Count Clicks ------------------
@app.route("/<code>")
def redirect_url(code):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT long_url, clicks FROM urls WHERE short_code=?", (code,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return "URL not found", 404

    cur.execute("UPDATE urls SET clicks=? WHERE short_code=?", (row["clicks"] + 1, code))
    conn.commit()
    conn.close()

    return redirect(row["long_url"])

# ------------------ Analytics Page ------------------
@app.route("/stats/<code>")
def stats(code):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT long_url, clicks, created_at FROM urls WHERE short_code=?", (code,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return "Not found", 404

    return render_template("stats.html", data=row, code=code)

# ------------------ REST API: Shorten URL ------------------
@app.route("/api/shorten", methods=["POST"])
def api_shorten():
    data = request.get_json()
    long_url = data["url"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("INSERT INTO urls (long_url, short_code, clicks) VALUES (?, ?, ?)",
                (long_url, "temp", 0))
    conn.commit()

    url_id = cur.lastrowid
    code = hashids.encode(url_id)

    cur.execute("UPDATE urls SET short_code=? WHERE id=?", (code, url_id))
    conn.commit()
    conn.close()

    return jsonify({
        "short_url": request.host_url + code,
        "code": code
    })

# ------------------ REST API: Analytics ------------------
@app.route("/api/stats/<code>")
def api_stats(code):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT long_url, clicks FROM urls WHERE short_code=?", (code,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "long_url": row["long_url"],
        "clicks": row["clicks"]
    })

# ------------------ Run Server ------------------
if __name__ == "__main__":
    app.run(debug=True)
