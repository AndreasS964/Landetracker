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

# Logging-Setup und globale Speicher
log_lines = []
missing = set()
aircraft_db = {}

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
DB_UPDATE_INTERVAL = 30 * 24 * 3600  # 30 days

# Haversine dist in NM
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 0.539957

# Datenbank initialisieren
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flugdaten (
            hex TEXT,
            callsign TEXT,
            baro_altitude REAL,
            velocity REAL,
            timestamp INTEGER,
            muster TEXT,
            lat REAL,
            lon REAL
        )""")
    conn.commit()
    conn.close()

# Muster-Datenbank aktualisieren
def update_aircraft_db():
    try:
        if os.path.exists(AIRCRAFT_CSV) and time.time() - os.path.getmtime(AIRCRAFT_CSV) < DB_UPDATE_INTERVAL:
            return
        url = 'https://raw.githubusercontent.com/VirtualRadarPlugin/AircraftList/master/resources/AircraftList.json'
        data = requests.get(url, timeout=30).json()
        with open(AIRCRAFT_CSV, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['icao', 'model'])
            for e in data:
                td = e.get('ICAOTypeDesignator','')
                model = e.get('Model') or e.get('Name','')
                if td:
                    w.writerow([td, model])
        log_lines.append(f"[{datetime.utcnow()}] Musterliste aktualisiert")
    except Exception as e:
        log_lines.append(f"[{datetime.utcnow()}] Fehler beim Laden der Musterliste: {e}")

# Muster laden
def load_aircraft_db():
    db = {}
    try:
        with open(AIRCRAFT_CSV, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                db[r['icao']] = r['model']
        log_lines.append(f"[{datetime.utcnow()}] Musterliste geladen")
    except Exception as e:
        log_lines.append(f"[{datetime.utcnow()}] Fehler beim Einlesen der Musterliste: {e}")
    return db

# Fetch and store
def fetch_and_store():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    while True:
        try:
            # readsb local
            data = requests.get('http://127.0.0.1:8080/data.json', timeout=5).json()
            ts = int(time.time())
            rows = []
            for ac in data.get('aircraft',[]):
                hexid = ac.get('hex')
                cs = (ac.get('flight') or '').strip()
                lat, lon, alt, vel = ac.get('lat'), ac.get('lon'), ac.get('alt_baro'), ac.get('gs')
                td = ac.get('t') or ''
                model = aircraft_db.get(td.strip(),'') or 'Unbekannt'
                if None in (lat, lon, alt): continue
                if haversine(EDTW_LAT, EDTW_LON, lat, lon) <= MAX_RADIUS_NM:
                    rows.append((hexid, cs, alt, vel, ts, model, lat, lon))
            if rows:
                cur.executemany('INSERT INTO flugdaten VALUES(?,?,?,?,?,?,?,?)', rows)
                conn.commit()
        except Exception:
            pass
        time.sleep(FETCH_INTERVAL)

class Handler(http.server.BaseHTTPRequestHandler):
    def render_main(self, params):
        rad = params.get('radius',['5'])[0]
        alt = params.get('altfilter',['all'])[0]
        date = params.get('date',[''])[0]
        # SQL query omitted for brevity
        rows_html = ''
        # DB read omitted
        html_content = f"""
<!DOCTYPE html>
<html lang='de'>
<head><meta charset='utf-8'><title>Flugtracker EDTW</title>
<link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'/>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
<style>body{{padding:20px;}}</style>
</head>
<body>
<div class='container'>
<h3>Flugtracker EDTW – Version {VERSION}</h3>
<div id='map' style='height:400px;'></div>
<table class='table'><thead><tr><th>Call</th><th>Alt</th></tr></thead><tbody>
{rows_html}
</tbody></table>
</div>
<script>
var map=L.map('map').setView([{EDTW_LAT},{EDTW_LON}],11);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
fetch('/api/flights').then(r=>r.json()).then(data=>{{
 data.forEach(ac=>{{
  L.circleMarker([ac.lat,ac.lon],{{radius:6}}).bindPopup(ac.callsign).addTo(map);
 }});
}});
</script>
</body>
</html>"""
        return html_content.encode('utf-8')

    def do_GET(self):
        p = urlparse(self.path)
        qs = parse_qs(p.query)
        if p.path=='/':
            out=self.render_main(qs)
            self.send_response(200)
            self.send_header('Content-Type','text/html')
            self.send_header('Content-Length',str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        elif p.path=='/api/flights':
            # JSON output omitted
            pass
        else:
            self.send_error(404)

if __name__=='__main__':
    init_db()
    update_aircraft_db()
    aircraft_db=load_aircraft_db()
    threading.Thread(target=fetch_and_store,daemon=True).start()
    with socketserver.TCPServer(('',PORT),Handler) as httpd:
        httpd.serve_forever()

