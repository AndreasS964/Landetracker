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
        r = requests.get(url, timeout=30)
        try:
            data = r.json()
        except Exception as e:
            logger.error(f"Fehler beim Parsen der JSON-Antwort: {e} – Inhalt war: {r.text[:100]}")
            return
        valid = [e for e in data if e.get('ICAOTypeDesignator')]
        if not valid:
            logger.error("Keine gültigen ICAOTypeDesignator in JSON-Daten gefunden.")
            return
        with open(AIRCRAFT_CSV, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['icao', 'model'])
            for e in valid:
                td = e.get('ICAOTypeDesignator','')
                m = e.get('Model') or e.get('Name','')
                w.writerow([td, m])
        logger.info(f"Musterliste erfolgreich aktualisiert: {len(valid)} Einträge")
    except Exception as e:
        logger.error(f"Fehler beim Laden der Musterliste: {e}")

# --- Aircraft DB laden ---
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

# --- Webserver ---
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path)
        if p.path == '/log':
            log_html = '<br>'.join(str(line) for line in log_lines[-50:])
            content = f'<html><head><meta charset="utf-8"><title>Log</title></head><body><h2>Log</h2><pre>{log_html}</pre><a href="/">Zurück</a></body></html>'.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif p.path == '/stats':
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    result = conn.execute("SELECT date(timestamp, 'unixepoch', 'localtime') as day, COUNT(*) FROM flugdaten GROUP BY day ORDER BY day DESC LIMIT 30").fetchall()
                stat_html = '<table border=1><tr><th>Tag</th><th>Landungen</th></tr>' + ''.join(f'<tr><td>{r[0]}</td><td>{r[1]}</td></tr>' for r in result) + '</table>'
                content = f'<html><head><meta charset="utf-8"><title>Statistiken</title></head><body><h2>Letzte 30 Tage</h2>{stat_html}<br><a href="/">Zurück</a></body></html>'.encode('utf-8')
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                logger.error(f"Fehler bei /stats: {e}")
                self.send_error(500, "Fehler beim Abrufen der Statistik")
        elif self.path == '/' or self.path == '/index.html':
            try:
                with open("index.html", "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_error(404, "index.html nicht gefunden")
        elif self.path == '/flights.json':
            try:
                cutoff = int(time.time()) - 7 * 86400
                with sqlite3.connect(DB_PATH) as conn:
                    rows = conn.execute("SELECT lat, lon, callsign, baro_altitude, velocity, timestamp FROM flugdaten WHERE timestamp > ?", (cutoff,)).fetchall()
                data = []
                for r in rows:
                    if not r[0] or not r[1]: continue
                    mode = ""
                    if r[3] is not None and r[3] < 1200 and haversine(r[0], r[1], EDTW_LAT, EDTW_LON) < 1:
                        mode = "arrival"
                    elif r[3] is not None and r[3] > 3000 and haversine(r[0], r[1], EDTW_LAT, EDTW_LON) < 1:
                        mode = "departure"
                    data.append({"lat": r[0], "lon": r[1], "cs": r[2], "alt": r[3], "vel": r[4], "timestamp": r[5], "mode": mode})
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

# --- Main ---
if __name__ == '__main__':
    init_db()
    update_aircraft_db()
    aircraft_db = load_aircraft_db()
    threading.Thread(target=fetch_and_store, daemon=True).start()
    threading.Thread(target=cleanup_old_data, daemon=True).start()
    logger.info(f"Starte Flugtracker v{VERSION} auf Port {PORT}...")
    print(f"✅ Flugtracker v{VERSION} läuft auf Port {PORT}")
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        logger.critical(f"HTTP-Server abgestürzt: {e}")
    finally:
        logger.info("Flugtracker beendet.")

