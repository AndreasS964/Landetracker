# flighttracker.py – vollständiger Gesamtstand (1. Mai 2025)

import http.server
import socketserver
import sqlite3
import requests
import time
import math
import csv
import json
import html
import threading
import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

PORT = 8083
DB_PATH = 'flugdaten.db'
AIRCRAFT_CSV = 'aircraft_db.csv'
READSB_DB_PATH = "/run/readsb/aircraft.json"
EDTW_LAT = 48.27889122038788
EDTW_LON = 8.42936618151063
VERSION = '1.9e'
GPX_FILE = 'platzrunde.gpx'
SETTINGS_FILE = 'settings.json'
FETCH_INTERVAL = 300
MAX_DATA_AGE = 180 * 86400
CLEANUP_INTERVAL = 86400

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

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 0.539957

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS flugdaten (
            hex TEXT, callsign TEXT, baro_altitude REAL,
            velocity REAL, timestamp INTEGER, muster TEXT,
            lat REAL, lon REAL)''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_time ON flugdaten(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_coords ON flugdaten(lat, lon)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_muster ON flugdaten(muster)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_callsign ON flugdaten(callsign)')
        conn.commit()

def load_aircraft_db():
    db = {}
    try:
        with open(AIRCRAFT_CSV, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                key = r['icao'].strip().upper()
                db[key] = r['model'].strip()
        logger.info(f"Musterliste geladen: {len(db)} Typen")
    except Exception as e:
        logger.error(f"Fehler beim Einlesen der Musterliste: {e}")
    return db

def load_readsb_aircraft_db():
    try:
        with open(READSB_DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Konnte readsb aircraft.json nicht laden: {e}")
        return {}

def bestimme_muster(flight, readsb_db, aircraft_db):
    icao = flight.get("hex", "").upper()
    typ = ""
    if icao in readsb_db and isinstance(readsb_db[icao], dict) and "type" in readsb_db[icao]:
        typ = readsb_db[icao]["type"].strip().upper()
    else:
        typ = flight.get("type", "").strip().upper()
    muster = aircraft_db.get(typ, typ if typ else icao)
    return muster

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

def fetch_adsblol():
    try:
        logger.info("adsb.lol-Datenabruf gestartet...")
        url = f"https://api.adsb.lol/v2/lat/{EDTW_LAT}/lon/{EDTW_LON}/dist/5"
        r = requests.get(url, timeout=10)
        if r.ok:
            data = r.json().get("aircraft", [])
            count = 0
            with sqlite3.connect(DB_PATH) as conn:
                for f in data:
                    if not f.get("hex") or not f.get("seen_pos"):
                        continue
                    flight = {
                        "hex": f.get("hex", "").upper(),
                        "callsign": f.get("flight", "").strip(),
                        "baro_altitude": f.get("alt_baro", 0),
                        "velocity": f.get("gs", 0),
                        "timestamp": int(time.time()),
                        "lat": f.get("lat"),
                        "lon": f.get("lon"),
                        "type": f.get("t", "")
                    }
                    flight["muster"] = bestimme_muster(flight, readsb_db, aircraft_db)
                    conn.execute('''INSERT INTO flugdaten VALUES (?,?,?,?,?,?,?,?)''',
                        (flight["hex"], flight["callsign"], flight["baro_altitude"],
                         flight["velocity"], flight["timestamp"], flight["muster"],
                         flight["lat"], flight["lon"]))
                    count += 1
                conn.commit()
            logger.info(f"{count} Flugdaten von adsb.lol gespeichert.")
        else:
            logger.warning(f"adsb.lol-Antwortstatus: {r.status_code}")
    except Exception as e:
        logger.error(f"Fehler beim adsb.lol-Abruf: {e}")

def watchdog_loop():
    while True:
        try:
            import systemd.daemon
            systemd.daemon.notify("WATCHDOG=1")
        except: pass
        time.sleep(60)

def load_platzrunde():
    try:
        with open(GPX_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Platzrunde konnte nicht geladen werden: {e}")
        return ""

def get_flight_data():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM flugdaten ORDER BY timestamp DESC LIMIT 500")
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Fehler beim Laden der Flugdaten: {e}")
        return []

def fetch_stats():
    out = {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            out["landungen"] = conn.execute("""
                SELECT date(timestamp, 'unixepoch', 'localtime') AS tag, COUNT(*) AS anzahl
                FROM flugdaten
                GROUP BY tag ORDER BY tag DESC LIMIT 30
            """).fetchall()
            out["muster"] = conn.execute("""
                SELECT muster, COUNT(*) AS anzahl FROM flugdaten
                GROUP BY muster ORDER BY anzahl DESC LIMIT 10
            """).fetchall()
            out["stunden"] = conn.execute("""
                SELECT strftime('%H', timestamp, 'unixepoch', 'localtime') AS stunde, COUNT(*) AS anzahl
                FROM flugdaten GROUP BY stunde ORDER BY stunde
            """).fetchall()
    except Exception as e:
        logger.error(f"Fehler bei Statistikabfrage: {e}")
    return {k: [dict(r) for r in v] for k, v in out.items()}

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/log":
            content = '<html><head><meta charset="utf-8"><title>Log</title></head><body><h2>Log</h2><pre>'
            content += '<br>'.join(html.escape(l) for l in log_lines[-100:])
            content += '</pre><a href="/">Zurück</a></body></html>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        elif parsed.path == "/stats":
            stats = fetch_stats()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode("utf-8"))
        elif parsed.path == "/flights.json":
            data = get_flight_data()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif parsed.path == "/api/adsb":
            fetch_adsblol()
            self.send_response(200)
            self.end_headers()
        elif parsed.path == "/export.csv":
            data = get_flight_data()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", "attachment; filename=flugdaten.csv")
            self.end_headers()
            w = csv.DictWriter(self.wfile, fieldnames=data[0].keys())
            w.writeheader()
            w.writerows(data)
        elif parsed.path == "/platzrunde.gpx":
            data = load_platzrunde()
            self.send_response(200)
            self.send_header("Content-Type", "application/gpx+xml")
            self.end_headers()
            self.wfile.write(data.encode("utf-8"))
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))
    init_db()
    aircraft_db = load_aircraft_db()
    readsb_db = load_readsb_aircraft_db()
    threading.Thread(target=cleanup_old_data, daemon=True).start()
    threading.Thread(target=watchdog_loop, daemon=True).start()
    threading.Thread(target=fetch_adsblol, daemon=True).start()
    logger.info(f"Starte Flugtracker v{VERSION} auf Port {PORT}...")
    print(f"✅ Flugtracker v{VERSION} läuft auf Port {PORT}")
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        logger.critical(f"HTTP-Server abgestürzt: {e}")
    finally:
        logger.info("Flugtracker beendet.")

