import sqlite3
from flask import Flask, jsonify, request, render_template
import os

app = Flask(__name__)
DB_FILE = "flights.db"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/flights")
def get_flights():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flights ORDER BY time DESC LIMIT 100")
    rows = cursor.fetchall()
    conn.close()
    return jsonify(rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)