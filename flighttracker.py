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
try:
    from systemd.daemon import notify
except ImportError:
    def notify(msg): pass

os.chdir(os.path.dirname(__file__))

# --- Konfiguration ---
PORT = 8083
DB_PATH = 'flugdaten.db'
AIRCRAFT_CSV = 'aircraft_db.csv'
EDTW_LAT = 48.27889122038788
EDTW_LON = 8.42936618151063
VERSION = '1.9'
FETCH_INTERVAL = 300
ADSBL_API = "https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{nm}"
CLEANUP_INTERVAL = 86400
MAX_DATA_AGE = 180 * 86400
WATCHDOG_INTERVAL = 60
GPX_FILE = 'platzrunde.gpx'
SETTINGS_FILE = 'settings.json'

# --- Settings laden ---
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"radius_nm": 5}

settings = load_settings()
current_radius_nm = settings.get("radius_nm", 5)

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

def load_platzrunde():
    try:
        with open(GPX_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Platzrunde konnte nicht geladen werden: {e}")
        return ""

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

def watchdog_loop():
    while True:
        notify("WATCHDOG=1")
        time.sleep(WATCHDOG_INTERVAL // 2)

def fetch_adsblol():
    try:
        logger.info("adsb.lol-Datenabruf gestartet...")
        url = f"https://api.adsb.lol/v2/lat/{EDTW_LAT}/lon/{EDTW_LON}/dist/{current_radius_nm}"
        r = requests.get(url, timeout=10)
        if r.ok:
            try:
                data = r.json()
                count = len(data.get("aircraft", []))
                logger.info(f"adsb.lol-Daten erfolgreich abgerufen ({len(r.content)} Bytes, {count} Flieger)")
            except Exception as e:
                logger.error(f"Fehler beim Parsen der adsb.lol-Daten: {e} – Inhalt war: {r.text[:100]}")
        else:
            logger.warning(f"adsb.lol-Antwortstatus: {r.status_code} – {r.text[:100]}")
    except Exception as e:
        logger.error(f"Fehler beim adsb.lol-Abruf: {e}")

def adsblol_loop():
    while True:
        try:
            fetch_adsblol()
        except Exception as e:
            logger.critical(f"adsblol_loop abgestürzt: {e}")
        time.sleep(FETCH_INTERVAL)

def fetch_stats():
    out = {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT date(timestamp, 'unixepoch', 'localtime') AS tag, COUNT(*) AS anzahl
                FROM flugdaten
                GROUP BY tag
                ORDER BY tag DESC
                LIMIT 30
            """)
            out = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Fehler bei Statistikabfrage: {e}")
    return out

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global current_radius_nm
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
        elif parsed.path == "/platzrunde.gpx":
            data = load_platzrunde()
            self.send_response(200)
            self.send_header("Content-Type", "application/gpx+xml")
            self.end_headers()
            self.wfile.write(data.encode("utf-8"))
        elif parsed.path == "/radius":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"radius_nm": current_radius_nm}).encode("utf-8"))
        elif parsed.path.startswith("/set_radius"):
            try:
                params = parse_qs(parsed.query)
                new_val = int(params.get("nm", [current_radius_nm])[0])
                current_radius_nm = new_val
                with open(SETTINGS_FILE, 'w') as f:
                    json.dump({"radius_nm": current_radius_nm}, f)
                logger.info(f"Radius geändert: {current_radius_nm} NM")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "radius": current_radius_nm}).encode("utf-8"))
            except Exception as e:
                logger.error(f"Fehler bei set_radius: {e}")
                self.send_error(500, str(e))
        elif parsed.path == "/links":
            content = '''<html><head><meta charset="utf-8"><title>Links</title></head><body>
            <h2>Externe Tools</h2>
            <ul>
              <li><a href="http://localhost/tar1090/" target="_blank">tar1090</a></li>
              <li><a href="http://localhost/graphs1090/" target="_blank">graphs1090</a></li>
            </ul>
            <a href="/">Zurück</a></body></html>'''
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == '__main__':
    init_db()
    update_aircraft_db()
    aircraft_db = load_aircraft_db()
    threading.Thread(target=cleanup_old_data, daemon=True).start()
    threading.Thread(target=watchdog_loop, daemon=True).start()
    threading.Thread(target=adsblol_loop, daemon=True).start()
    logger.info(f"Starte Flugtracker v{VERSION} auf Port {PORT}...")
    print(f"✅ Flugtracker v{VERSION} läuft auf Port {PORT}")
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        logger.critical(f"HTTP-Server abgestürzt: {e}")
    finally:
        logger.info("Flugtracker beendet.")
