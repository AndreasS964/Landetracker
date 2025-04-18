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
import socket
import pyModeS as pms

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
GPX_FILE = 'platzrunde.gpx'

log_lines = []
class WebLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            log_lines.append(msg)
            if len(log_lines) > 1000:
                log_lines.pop(0)
        except Exception:
            pass

logger = logging.getLogger("tracker")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
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
        resp = requests.get(url, timeout=30)
        data = resp.json()
        entries = data.get('Aircraft', [])
        with open(AIRCRAFT_CSV, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['icao', 'model'])
            for e in entries:
                td = e.get('ICAOTypeDesignator', '')
                m = e.get('Model') or e.get('Name', '')
                if td:
                    w.writerow([td, m])
        logger.info(f"Musterliste aktualisiert: {len(entries)} Einträge")
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

def fetch_beast_and_store():
    global aircraft_db
    while True:
        try:
            with socket.create_connection(("127.0.0.1", 30005), timeout=10) as sock:
                sock.settimeout(2)
                logger.info("Beast-Modus: Verbindung zu Port 30005 hergestellt.")
                while True:
                    data = sock.recv(4096)
                    if not data:
                        break
                    messages = pms.socket.reader(data)
                    ts = int(time.time())
                    rows = []
                    for msg in messages:
                        try:
                            icao = pms.adsb.icao(msg)
                            cs = pms.adsb.callsign(msg) or ''
                            alt = pms.adsb.altitude(msg)
                            pos = pms.adsb.position_with_ref(msg, EDTW_LAT, EDTW_LON)
                            vel = pms.adsb.velocity(msg)[0] if pms.adsb.velocity(msg) else None
                            if pos is None or alt is None:
                                continue
                            lat, lon = pos
                            if haversine(EDTW_LAT, EDTW_LON, lat, lon) <= MAX_RADIUS_NM:
                                model = aircraft_db.get(icao.upper(), 'Unbekannt')
                                rows.append((icao, cs.strip(), alt, vel, ts, model, lat, lon))
                        except:
                            continue
                    if rows:
                        with sqlite3.connect(DB_PATH) as conn:
                            conn.executemany('INSERT INTO flugdaten VALUES (?,?,?,?,?,?,?,?)', rows)
                            conn.commit()
                        logger.info(f"{len(rows)} Flüge aus Beast-Daten gespeichert.")
        except Exception as e:
            logger.error(f"Fehler bei Beast-Verbindung: {e}")
            time.sleep(10)

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

# Handler bleibt unverändert ...

if __name__ == '__main__':
    init_db()
    update_aircraft_db()
    aircraft_db = load_aircraft_db()
    threading.Thread(target=fetch_beast_and_store, daemon=True).start()
    threading.Thread(target=cleanup_old_data, daemon=True).start()
    logger.info(f"Starte Flugtracker v{VERSION} auf Port {PORT}...")
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        logger.critical(f"HTTP-Server abgestürzt: {e}")
    finally:
        logger.info("Flugtracker beendet.")

