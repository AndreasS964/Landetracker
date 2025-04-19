import http.server
import socketserver
import sqlite3
import requests
import time
import math
from datetime import datetime
import csv
import json
from urllib.parse import urlparse, parse_qs
import html
import threading
import sys
import os
import logging
from logging.handlers import RotatingFileHandler

# --- Konfiguration ---
PORT = 8083
DB_PATH = 'flugdaten.db'
AIRCRAFT_CSV = 'aircraft_db.csv'
EDTW_LAT = 48.27889122038788
EDTW_LON = 8.42936618151063
MAX_RADIUS_NM = 5
VERSION = '1.7'
FETCH_INTERVAL = 300
CLEANUP_INTERVAL = 86400
MAX_DATA_AGE = 180 * 86400

# --- Logging einrichten ---
log_lines = []

class WebLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        log_lines.append(msg)
        if len(log_lines) > 1000:
            log_lines.pop(0)

logger = logging.getLogger("tracker")
logger.setLevel(logging.INFO)
fh = RotatingFileHandler("tracker.log", maxBytes=2_000_000, backupCount=3)
fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
wh = WebLogHandler()
wh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(fh)
logger.addHandler(wh)

# --- Haversine ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 0.539957

# --- Init DB ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS flugdaten (
                hex TEXT,
                callsign TEXT,
                baro_altitude REAL,
                velocity REAL,
                timestamp INTEGER,
                muster TEXT,
                lat REAL,
                lon REAL
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_time ON flugdaten(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_coords ON flugdaten(lat, lon)')
        conn.commit()

# --- Aircraft DB aktualisieren ---
def update_aircraft_db():
    try:
        if os.path.exists(AIRCRAFT_CSV) and time.time() - os.path.getmtime(AIRCRAFT_CSV) < 180 * 86400:
            return
        url = 'https://raw.githubusercontent.com/VirtualRadarPlugin/AircraftList/master/resources/AircraftList.json'
        data = requests.get(url, timeout=30).json()
        with open(AIRCRAFT_CSV, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['icao', 'model'])
            for e in data:
                td = e.get('ICAOTypeDesignator','')
                m = e.get('Model') or e.get('Name','')
                if td:
                    w.writerow([td, m])
        logger.info(f"Musterliste aktualisiert: {len(data)} Einträge")
    except Exception as e:
        logger.error(f"Fehler beim Laden der Musterliste: {e}")

def load_aircraft_db():
    db = {}
    try:
        with open(AIRCRAFT_CSV, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                db[r['icao']] = r['model']
        logger.info(f"Musterliste geladen: {len(db)} Typen")
    except Exception as e:
        logger.error(f"Fehler beim Einlesen der Musterliste: {e}")
    return db

# --- Fetch Daten ---
def fetch_and_store():
    global aircraft_db
    while True:
        try:
            data = requests.get('http://127.0.0.1:8080/data.json', timeout=5).json()
            ts = int(time.time())
            rows = []
            for ac in data.get('aircraft', []):
                lat, lon, alt, vel = ac.get('lat'), ac.get('lon'), ac.get('alt_baro'), ac.get('gs')
                if None in (lat, lon, alt): continue
                if haversine(EDTW_LAT, EDTW_LON, lat, lon) <= MAX_RADIUS_NM:
                    cs = (ac.get('flight') or '').strip()
                    model = aircraft_db.get(ac.get('t') or '', 'Unbekannt')
                    rows.append((ac.get('hex'), cs, alt, vel, ts, model, lat, lon))
            if rows:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.executemany('INSERT INTO flugdaten VALUES (?,?,?,?,?,?,?,?)', rows)
                    conn.commit()
            logger.info(f"{len(rows)} neue Flüge gespeichert.")
        except Exception as e:
            logger.error(f"Fehler bei fetch_and_store: {e}")
        time.sleep(FETCH_INTERVAL)

# --- Cleanup ---
def cleanup_old_data():
    while True:
        try:
            cutoff = int(time.time()) - MAX_DATA_AGE
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute('DELETE FROM flugdaten WHERE timestamp < ?', (cutoff,))
                conn.commit()
            logger.info("Datenbereinigung durchgeführt.")
        except Exception as e:
            logger.error(f"Fehler bei Datenbereinigung: {e}")
        time.sleep(CLEANUP_INTERVAL)

# --- Main ---
if __name__ == '__main__':
    import mimetypes

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/log':
                log_html = '<br>'.join(str(line) for line in log_lines[-50:])
                content = f'<html><head><meta charset=\"utf-8\"><title>Log</title></head><body><h2>Log</h2><pre>{log_html}</pre><a href=\"/\">Zurück</a></body></html>'.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            elif self.path == '/' or self.path == '/index.html':
                if not os.path.exists("index.html"):
                    with open("index.html", "w", encoding="utf-8") as f:
                        f.write("""<!DOCTYPE html>
<html lang='de'>
<head><meta charset='UTF-8'><title>Flugtracker</title>
<link rel='stylesheet' href='https://unpkg.com/leaflet/dist/leaflet.css'/>
<style>html,body{margin:0;padding:0;height:100%;}#map{height:100%;}</style>
</head><body>
<div id='map'></div>
<script src='https://unpkg.com/leaflet/dist/leaflet.js'></script>
<script>
const map = L.map('map').setView([48.2789,8.4293],11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18}).addTo(map);
fetch('/flights.json').then(r=>r.json()).then(data=>{
data.forEach(f=>L.marker([f.lat,f.lon]).addTo(map).bindPopup(f.cs + '<br>' + f.alt + ' ft'));
});</script></body></html>""")
                try:
                    with open("index.html", "rb") as f:
                        content = f.read()
                        self.send_response(200)
                        self.send_header("Content-Type", mimetypes.guess_type("index.html")[0])
                        self.send_header("Content-Length", str(len(content)))
                        self.end_headers()
                        self.wfile.write(content)
                except FileNotFoundError:
                    self.send_error(404, "index.html nicht gefunden")
            elif self.path == '/flights.json':
                try:
                    cutoff = int(time.time()) - 300
                    with sqlite3.connect(DB_PATH) as conn:
                        rows = conn.execute("SELECT lat, lon, callsign, baro_altitude FROM flugdaten WHERE timestamp > ?", (cutoff,)).fetchall()
                    data = [{"lat": r[0], "lon": r[1], "cs": r[2], "alt": r[3]} for r in rows if r[0] and r[1]]
                    payload = json.dumps(data).encode('utf-8')
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except Exception as e:
                    logger.error(f"Fehler bei /flights.json: {e}")
                    self.send_error(500, "Fehler beim Abrufen der Flugdaten")
            else:
                self.send_error(404, "Nicht gefunden")

    init_db()
    update_aircraft_db()
    aircraft_db = load_aircraft_db()

    threading.Thread(target=fetch_and_store, daemon=True).start()
    threading.Thread(target=cleanup_old_data, daemon=True).start()

    logger.info(f"Starte Flugtracker v{VERSION} auf Port {PORT}...")
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        logger.critical(f"HTTP-Server abgestürzt: {e}")
    finally:
        logger.info("Flugtracker beendet.")
