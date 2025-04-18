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
READSB_URL = 'http://127.0.0.1:8080/data.json'

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

def fetch_and_store():
    global aircraft_db
    while True:
        try:
            r = requests.get(READSB_URL, timeout=5)
            if r.status_code != 200:
                logger.warning(f"readsb JSON nicht erreichbar: Status {r.status_code}")
                time.sleep(FETCH_INTERVAL)
                continue
            data = r.json()
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

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path)
        if p.path == '/':
            html = f"""
<!DOCTYPE html><html lang='de'><head><meta charset='utf-8'><title>Flugtracker</title>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'/>
<link rel='stylesheet' href='https://cdn.datatables.net/1.10.24/css/jquery.dataTables.min.css'/>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/>
<script src='https://code.jquery.com/jquery-3.6.0.min.js'></script>
<script src='https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js'></script>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
</head><body><div class='container'><h2>Flugtracker v{VERSION}</h2>
<div id='map' style='height:400px;'></div>
<table id='flugtable' class='table'><thead><tr><th>Call</th><th>Alt</th><th>Speed</th><th>Muster</th><th>Zeit</th><th>Datum</th></tr></thead><tbody></tbody></table>
<a href='/log'>Log anzeigen</a></div>
<script>
var map = L.map('map').setView([{EDTW_LAT}, {EDTW_LON}], 12);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{attribution:'© OSM'}}).addTo(map);
var platzrunde=[[48.2797,8.4276],[48.2693,8.4372],[48.2643,8.4497],[48.2766,8.4735],[48.3194,8.4271],[48.3067,8.3984],[48.2888,8.4186],[48.2803,8.4271],[48.2797,8.4276]];
L.polygon(platzrunde,{{color:'blue',weight:2,fill:false}}).addTo(map);
var layer=L.layerGroup().addTo(map);
function reload(){{
fetch('/api/flights').then(r=>r.json()).then(data=>{{
layer.clearLayers();
let html='';
data.forEach(a=>{{
if(!a.lat||!a.lon)return;
let col=a.baro_altitude<3000?'green':a.baro_altitude<5000?'orange':'red';
L.circleMarker([a.lat,a.lon],{{radius:6,color:col}}).bindPopup(a.callsign).addTo(layer);
let t=new Date(a.timestamp*1000);
html+="<tr><td>"+a.callsign+"</td><td>"+Math.round(a.baro_altitude)+"</td><td>"+Math.round(a.velocity || 0)+"</td><td>"+a.muster+"</td><td>"+t.toLocaleTimeString()+"</td><td>"+t.toLocaleDateString()+"</td></tr>";
}});
$('#flugtable').DataTable().clear().destroy();
$('#flugtable tbody').html(html);
$('#flugtable').DataTable();
}});
}}
reload();setInterval(reload,60000);
</script></body></html>""".encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        elif p.path == '/log':
            content = f"<html><head><meta charset='utf-8'></head><body><h3>Log</h3><pre>{'<br>'.join(log_lines[-50:])}</pre><a href='/'>Zurück</a></body></html>".encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','text/html')
            self.send_header('Content-Length',str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif p.path == '/api/flights':
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute('SELECT callsign, baro_altitude, velocity, timestamp, muster, lat, lon FROM flugdaten ORDER BY timestamp DESC LIMIT 100').fetchall()
                js = json.dumps([dict(r) for r in rows], ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(js)))
            self.end_headers()
            self.wfile.write(js)

if __name__ == '__main__':
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
