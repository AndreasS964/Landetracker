import http.server
import socketserver
import sqlite3
import requests
import time
import math
from datetime import datetime
import csv
from urllib.parse import urlparse, parse_qs
import html
import threading
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from string import Template

# Configuration
PORT = 8083
DB_PATH = 'flugdaten.db'
AIRCRAFT_CSV = 'aircraft_db.csv'
MISSING_LOG = 'missing_muster.log'
EDTW_LAT = 48.27889122038788
EDTW_LON = 8.42936618151063
MAX_RADIUS_NM = 5
VERSION = '1.6'
FETCH_INTERVAL = 300  # seconds
WATCHDOG_INTERVAL = 10  # seconds
DB_UPDATE_INTERVAL = 30 * 24 * 3600  # 30 days

# URLs
AIRCRAFT_LIST_URL = (
    'https://raw.githubusercontent.com/VirtualRadarPlugin/'
    'AircraftList/master/resources/AircraftList.json'
)

# Logging setup
logger = logging.getLogger('flugtracker')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('flugtracker.log', maxBytes=5*1024*1024, backupCount=3)
handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(handler)
log_lines = []

# Thread control
device_available = os.path.exists('/dev/watchdog')
shutdown_event = threading.Event()
fetch_thread = None
missing = set()
aircraft_db = {}

# Haversine dist in nm
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 0.539957

# Initial DB creation
def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''CREATE TABLE flugdaten (
                            hex TEXT,
                            callsign TEXT,
                            baro_altitude REAL,
                            velocity REAL,
                            timestamp INTEGER,
                            muster TEXT
                        )''')
        conn.commit()
        conn.close()

# Update aircraft DB
def update_aircraft_db():
    try:
        if os.path.exists(AIRCRAFT_CSV) and time.time() - os.path.getmtime(AIRCRAFT_CSV) < DB_UPDATE_INTERVAL:
            return
        r = requests.get(AIRCRAFT_LIST_URL, timeout=30)
        data = r.json()
        with open(AIRCRAFT_CSV, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['icao', 'model'])
            for e in data:
                td = e.get('ICAOTypeDesignator', '')
                m = e.get('Model') or e.get('Name', '')
                if td:
                    w.writerow([td, m])
        logger.info(f"Aircraft DB: {len(data)} entries")
    except Exception as e:
        logger.error(f"update error: {e}")

# Load aircraft DB
def load_aircraft_db():
    db = {}
    try:
        with open(AIRCRAFT_CSV, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                db[r['icao']] = r['model']
        logger.info(f"Loaded {len(db)} types")
    except Exception as e:
        logger.error(f"load error: {e}")
    return db

# Fetch thread mit OpenSky + readsb Unterstützung & Dublettenprüfung
def fetch_and_store():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    seen = set()
    while not shutdown_event.is_set():
        rows = []
        all_sources = []
        try:
            # OpenSky
            r = requests.get('https://opensky-network.org/api/states/all', timeout=10)
            if r.status_code == 200:
                all_sources.extend(r.json().get('states', []))
        except Exception as e:
            logger.warning(f"OpenSky-Fehler: {e}")

        try:
            # readsb JSON from localhost (tar1090 backend)
            r = requests.get('http://127.0.0.1/data/aircraft.json', timeout=10)
            if r.status_code == 200:
                json_data = r.json()
                for a in json_data.get('aircraft', []):
                    hexid = a.get('hex')
                    cs = a.get('flight', '').strip()
                    lat = a.get('lat')
                    lon = a.get('lon')
                    alt = a.get('alt_baro')
                    vel = a.get('gs')
                    td = a.get('t') or ''
                    all_sources.append([hexid, cs, lon, lat, alt, td, None, vel])
        except Exception as e:
            logger.warning(f"readsb-Fehler: {e}")

        ts = int(time.time())
        cnt = sav = 0
        for s in all_sources:
            cnt += 1
            hexid, cs = s[0], (s[1] or '').strip()
            lon, lat, alt, td, vel = s[2], s[3], s[4], s[5], s[7]
            model = aircraft_db.get((td or '').strip(), '')
            if not model:
                if hexid not in missing:
                    missing.add(hexid)
                    open(MISSING_LOG, 'a').write(f"{datetime.utcnow()} Missing {hexid}\n")
                model = 'Unbekannt'
            if None in (lat, lon, alt) or (hexid, ts) in seen:
                continue
            seen.add((hexid, ts))
            if haversine(EDTW_LAT, EDTW_LON, lat, lon) <= MAX_RADIUS_NM:
                rows.append((hexid, cs, alt, vel, ts, model))
                sav += 1

        if rows:
            cur.executemany('INSERT INTO flugdaten VALUES(?,?,?,?,?,?)', rows)
            conn.commit()

        msg = f"[{datetime.utcnow()}] {cnt} geprüft → {sav} gespeichert"
        log_lines.append(msg)
        logger.info(msg)
        shutdown_event.wait(FETCH_INTERVAL)
    conn.close()
