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

# Globals
PORT = 8083
DB_PATH = 'flugdaten.db'
AIRCRAFT_CSV = 'aircraft_db.csv'
MISSING_LOG = 'missing_muster.log'
EDTW_LAT = 48.27889122038788
EDTW_LON = 8.42936618151063
MAX_RADIUS_NM = 5  # Nautical miles
VERSION = '1.6'
FETCH_INTERVAL = 300  # seconds
DB_UPDATE_INTERVAL = 30 * 24 * 3600  # 30 days

# In-memory storage
log_lines = []
aircraft_db = {}
missing = set()

# Utilities

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 0.539957  # km to NM

# Database initialization

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS flugdaten (
        hex TEXT,
        callsign TEXT,
        baro_altitude REAL,
        velocity REAL,
        timestamp INTEGER,
        muster TEXT,
        lat REAL,
        lon REAL
    )''')
    conn.commit()
    conn.close()

# Aircraft type database
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
                td = e.get('ICAOTypeDesignator', '')
                model = e.get('Model') or e.get('Name', '')
                if td:
                    w.writerow([td, model])
        log_lines.append(f"[{datetime.utcnow()}] Musterliste aktualisiert: {len(data)} Einträge")
    except Exception as e:
        log_lines.append(f"[{datetime.utcnow()}] Fehler Muster-Update: {e}")


def load_aircraft_db():
    db = {}
    try:
        with open(AIRCRAFT_CSV, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                db[r['icao']] = r['model']
        log_lines.append(f"[{datetime.utcnow()}] Musterliste geladen: {len(db)} Typen")
    except Exception as e:
        log_lines.append(f"[{datetime.utcnow()}] Fehler Muster-Lesen: {e}")
    return db

# Data fetcher thread
def fetch_and_store():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    while True:
        try:
            r = requests.get('http://127.0.0.1:8080/data.json', timeout=5)
            data = r.json()
            ts = int(time.time())
            rows = []
            for ac in data.get('aircraft', []):
                lat, lon, alt, vel = ac.get('lat'), ac.get('lon'), ac.get('alt_baro'), ac.get('gs')
                hexid = ac.get('hex')
                cs = (ac.get('flight') or '').strip()
                td = ac.get('t') or ''
                model = aircraft_db.get(td.strip(), 'Unbekannt')
                if None in (lat, lon, alt): continue
                if haversine(EDTW_LAT, EDTW_LON, lat, lon) <= MAX_RADIUS_NM:
                    rows.append((hexid, cs, alt, vel, ts, model, lat, lon))
            if rows:
                cur.executemany('INSERT INTO flugdaten VALUES (?,?,?,?,?,?,?,?)', rows)
                conn.commit()
                log_lines.append(f"[{datetime.utcnow()}] {len(rows)} Flüge gespeichert")
        except Exception:
            pass
        time.sleep(FETCH_INTERVAL)

class Handler(http.server.BaseHTTPRequestHandler):
    def render_main(self, params):
        rad = params.get('radius',['5'])[0]
        altf = params.get('altfilter',['all'])[0]
        date = params.get('date',[''])[0]
        # Build SQL
        q = 'SELECT callsign, baro_altitude, velocity, timestamp, muster, lat, lon FROM flugdaten'
        cond = []
        if altf != 'all': cond.append(f'baro_altitude < {int(altf)}')
        if date:
            d0 = datetime.fromisoformat(date)
            start, end = int(d0.replace(hour=0,minute=0,second=0).timestamp()), int(d0.replace(hour=23,minute=59,second=59).timestamp())
            cond.append(f'timestamp BETWEEN {start} AND {end}')
        if cond: q += ' WHERE ' + ' AND '.join(cond)
        q += ' ORDER BY timestamp DESC LIMIT 100'
        conn = sqlite3.connect(DB_PATH)
        rows_html = ''
        for r in conn.execute(q):
            t = datetime.utcfromtimestamp(r[3]).strftime('%H:%M:%S')
            d = datetime.utcfromtimestamp(r[3]).date()
            rows_html += f"<tr><td>{html.escape(r[0])}</td><td>{r[1]:.0f}</td><td>{r[2]:.0f}</td><td>{html.escape(r[4])}</td><td>{t}</td><td>{d}</td></tr>"
        conn.close()
        # Render HTML
        html_content = f"""
<!DOCTYPE html>
<html lang='de'>
<head><meta charset='utf-8'><title>Flugtracker EDTW</title>
<link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'/>
<link rel='stylesheet' href='https://cdn.datatables.net/1.10.24/css/jquery.dataTables.min.css'/>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/>
<script src='https://code.jquery.com/jquery-3.6.0.min.js'></script>
<script src='https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js'></script>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
<style>body{{padding:20px;}}table{{width:100%;border-collapse:collapse;}}th,td{{border:1px solid #ccc;padding:6px;}}th{{background:#eee;}}.low{{color:green;}}.mid{{color:orange;}}.high{{color:red;}}</style>
</head>
<body>
<div class='container'>
  <img src="http://www.lsv-schwarzwald.de/wp-content/uploads/2013/04/lsv_logo.gif" style="height:40px;vertical-align:middle;margin-right:20px;">

  <h3>Flugtracker EDTW – Version {VERSION}</h3>
  <div><a href='/log'>Log</a> <a href='/stats'>Stats</a> <a href='/reset'>Reset DB</a></div>
  <div style='margin:10px 0;'><a href='/tar1090'>tar1090</a> <a href='/graphs1090'>graphs1090</a></div>
  <form method='GET' action='/'><label>Radius(nm):<input type='number' name='radius' value='{rad}'/></label> <label>Höhe:<select name='altfilter'><option value='all'{' selected' if altf=='all' else ''}>Alle</option><option value='3000'{' selected' if altf=='3000' else ''}><3000ft</option><option value='5000'{' selected' if altf=='5000' else ''}><5000ft</option></select></label> <label>Datum:<input type='date' name='date' value='{date}'/></label> <button>Filter</button></form>
  <div id='map' style='height:300px;margin:10px 0;'></div>
  <table id='flugtable'><thead><tr><th>Call</th><th>Alt</th><th>Vel</th><th>Muster</th><th>Zeit</th><th>Datum</th></tr></thead><tbody>{rows_html}</tbody></table>
</div>
<script>
  $$(document).ready(function(){{
    $('#flugtable').DataTable();
  }});
  var map = L.map('map').setView([{EDTW_LAT},{EDTW_LON}],11);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{attribution:'© OpenStreetMap'}).addTo(map);
  var layer = L.layerGroup().addTo(map);
  fetch('/api/flights').then(r=>r.json()).then(data=>{{
    .then(r=>r.json())
    .then(data=>{
      layer.clearLayers();
      data.forEach(a=>{{
        if (!a.lat || !a.lon) return;
        var col = a.baro_altitude<3000?'green':a.baro_altitude<5000?'orange':'red';
        L.circleMarker([a.lat,a.lon],{radius:6,color:col,fillOpacity:0.8}).bindPopup(a.callsign).addTo(layer);
      });
      document.getElementById('infobox').textContent = `Angezeigt: ${data.length} Flugzeuge (${new Date().toLocaleTimeString()})`;
    });
  // Korrigiere tar1090 und graphs1090 Links auf Port 80
  var host = window.location.hostname;
  document.querySelector("a[href='/tar1090']").href = 'http://' + host + '/tar1090';
  document.querySelector("a[href='/graphs1090']").href = 'http://' + host + '/graphs1090';
</script>
</body>
</html>"""
        return html_content.encode('utf-8')

    def do_GET(self):
        p = urlparse(self.path)
        qs = parse_qs(p.query)
        if p.path == '/':
            out = self.render_main(qs)
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        elif p.path == '/api/flights':
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            rows = conn.execute('SELECT callsign,baro_altitude,velocity,timestamp,muster,lat,lon FROM flugdaten ORDER BY timestamp DESC LIMIT 100').fetchall()
            conn.close()
            data = [dict(r) for r in rows]
            js = json.dumps(data, ensure_ascii=False)
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(js.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(js.encode('utf-8'))
        elif p.path == '/reset':
            sqlite3.connect(DB_PATH).execute('DELETE FROM flugdaten');
            self.send_response(303)
            self.send_header('Location','/')
            self.end_headers()
        else:
            self.send_error(404)

if __name__ == '__main__':
    init_db()
    update_aircraft_db()
    aircraft_db = load_aircraft_db()
    threading.Thread(target=fetch_and_store, daemon=True).start()
    print(f"[INFO] Starte Flugtracker v{VERSION} auf Port {PORT}...")
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Beende Flugtracker...")
            httpd.server_close()
            sys.exit(0)
