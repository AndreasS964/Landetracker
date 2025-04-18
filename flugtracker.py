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
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from string import Template

# Logging-Setup und globale Speicher
log_lines = []
missing = set()
aircraft_db = {}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 0.539957


def load_aircraft_db():
    db = {}
    try:
        with open(AIRCRAFT_CSV, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                db[r['icao']] = r['model']
        log_lines.append(f"[{datetime.utcnow()}] Musterliste geladen: {len(db)} Typen")
    except Exception as e:
        log_lines.append(f"[{datetime.utcnow()}] Fehler beim Einlesen der Musterliste: {e}")
    return db


def fetch_and_store():
    readsb_url = 'http://127.0.0.1:8080/data.json'
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    while True:
        try:
            r = requests.get(readsb_url, timeout=5)
            data = r.json()
            now = int(time.time())
            rows = []
            for ac in data.get('aircraft', []):
                hexid = ac.get('hex')
                cs = (ac.get('flight') or '').strip()
                alt = ac.get('alt_baro')
                vel = ac.get('gs')
                lat = ac.get('lat')
                lon = ac.get('lon')
                td = ac.get('t') or ''
                model = aircraft_db.get(td.strip(), '')
                if not model and hexid and hexid not in missing:
                    missing.add(hexid)
                    open(MISSING_LOG, 'a').write(f"{datetime.utcnow()} Missing {hexid}\\n")
                    model = 'Unbekannt'
                if None in (lat, lon, alt):
                    continue
                if haversine(EDTW_LAT, EDTW_LON, lat, lon) <= MAX_RADIUS_NM:
                    rows.append((hexid, cs, alt, vel, now, model, lat, lon))
            if rows:
                cur.executemany('INSERT INTO flugdaten VALUES(?,?,?,?,?,?,?,?)', rows)
                conn.commit()
                log_lines.append(f"[{datetime.utcnow()}] {len(rows)} Flüge gespeichert")
        except Exception as e:
            log_lines.append(f"[{datetime.utcnow()}] Fehler beim Abruf: {e}")
        time.sleep(FETCH_INTERVAL)


# Datenbankinitialisierung

def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''CREATE TABLE flugdaten (
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

# Flugzeug-Musterdaten aktualisieren und laden

AIRCRAFT_LIST_URL = 'https://raw.githubusercontent.com/VirtualRadarPlugin/AircraftList/master/resources/AircraftList.json'

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
        log_lines.append(f"[{datetime.utcnow()}] Musterliste aktualisiert: {len(data)} Einträge")
    except Exception as e:
        log_lines.append(f"[{datetime.utcnow()}] Fehler beim Laden der Musterliste: {e}")

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

# HTML Template mit Bootstrap, Farben, Karte & Links zu tar1090/graphs1090
MAIN_TEMPLATE = Template(r"""
<!DOCTYPE html>
<html lang=\"de\"><head><meta charset=\"utf-8\">
<title>Flugtracker EDTW</title>
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
<link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\" />
<script src=\"https://code.jquery.com/jquery-3.6.0.min.js\"></script>
<script src=\"https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js\"></script>
<script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"></script>
<script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\"></script>
<style>body{padding:20px;} table.dataTable tbody tr:hover{background:#f0f0f0;} .low{color:green;} .mid{color:orange;} .high{color:red;}</style>
</head><body>
<div class=\"container\">
<div class="alert alert-info p-2 mb-3" id="infobox" style="font-size: small;">
  Lade Flugzeugdaten …
</div>
<h3 class=\"mb-3\">Flugtracker EDTW – Version $version</h3>
<div class=\"mb-3\">
  <a href=\"/log\" class=\"btn btn-secondary btn-sm\">Log</a>
  <a href=\"/stats\" class=\"btn btn-secondary btn-sm\">Statistik</a>
  <a href=\"/reset\" class=\"btn btn-danger btn-sm\" onclick=\"return confirm('DB wirklich löschen?');\">DB zurücksetzen</a>
  <a href=\"/tar1090\" class=\"btn btn-outline-primary btn-sm\" target=\"_blank\">tar1090</a>
  <a href=\"/graphs1090\" class=\"btn btn-outline-primary btn-sm\" target=\"_blank\">graphs1090</a>
  <a href=\"/export.csv\" class=\"btn btn-outline-secondary btn-sm\">CSV Export</a>
  <a href=\"/update_muster\" class=\"btn btn-outline-info btn-sm\">Muster aktualisieren</a>
</div>
<form method=\"GET\" action=\"/\" class=\"row g-3\">
  <div class=\"col-auto\">
    <label class=\"form-label\">Radius (nm)</label>
    <input type=\"number\" name=\"radius\" value=\"$radius\" class=\"form-control\">
  </div>
  <div class=\"col-auto\">
    <label class=\"form-label\">Höhenfilter</label>
    <select name=\"altfilter\" class=\"form-select\">
      <option value=\"all\" $altall>Alle</option>
      <option value=\"3000\" $alt3000><3000ft</option>
      <option value=\"5000\" $alt5000><5000ft</option>
    </select>
  </div>
  <div class=\"col-auto\">
    <label class=\"form-label\">Datum</label>
    <input type=\"date\" name=\"date\" value=\"$date\" class=\"form-control\">
  </div>
  <div class=\"col-auto align-self-end\">
    <button type=\"submit\" class=\"btn btn-primary\">Anzeigen</button>
  </div>
</form>
<div id=\"map\" style=\"height:400px;margin-top:20px;\"></div>
<table id=\"flugtable\" class=\"table table-striped\"><thead><tr>
<th>Call</th><th>Höhe</th><th>Geschw.</th><th>Muster</th><th>Zeit</th><th>Datum</th></tr></thead><tbody>$rows</tbody></table>
<p class=\"text-muted small\">© Andreas Sika – Version $version</p>
</div>
<script>
$(document).ready(function() { $('#flugtable').DataTable(); });
setInterval(function() { location.reload(); }, 60000);
var map = L.map('map').setView([$lat, $lon], 11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap-Mitwirkende'
}).addTo(map);
var aircraftLayer = L.layerGroup().addTo(map);
L.circle([$lat, $lon], {radius: $radius_m, color: 'blue'}).addTo(map);

// Live-Flugzeugdaten von /api/flights holen und als Marker darstellen
fetch('/api/flights')
  .then(res => res.json())
  .then(data => {
    data.forEach(ac => {
      if (!ac.baro_altitude || !ac.callsign) return;
      let color = ac.baro_altitude < 3000 ? 'green' : ac.baro_altitude < 5000 ? 'orange' : 'red';
      let marker = L.circleMarker([ac.lat, ac.lon], {
        radius: 6,
        color: color,
        fillOpacity: 0.8
      }).bindPopup(`${ac.callsign}<br>${ac.baro_altitude} ft`);
      aircraftLayer.addLayer(marker);
    });
    document.getElementById('infobox').textContent = `Angezeigt: ${data.length} Flugzeuge (${new Date().toLocaleTimeString()})`;
    });
  });
</script>
</body></html>
""")

LOG_TEMPLATE = Template("""
<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><title>Log</title></head><body>
<h2>Log</h2><pre>$content</pre><a href="/">Zurück</a>
</body></html>
""")

STATS_TEMPLATE = Template("""
<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><title>Stats</title></head><body>
<h2>Statistik</h2><p>Einträge: $count<br>Letzter: $latest</p><a href="/">Zurück</a>
</body></html>
""")

class Handler(http.server.BaseHTTPRequestHandler):
    def export_csv(self):
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        rows = cur.execute("SELECT * FROM flugdaten ORDER BY timestamp DESC LIMIT 500").fetchall()
        con.close()

        self.send_response(200)
        self.send_header("Content-Type", "text/csv")
        self.send_header("Content-Disposition", "attachment; filename=flugdaten.csv")
        self.end_headers()

        writer = csv.writer(self.wfile)
        writer.writerow(["hex", "callsign", "alt", "velocity", "timestamp", "muster"])
        for r in rows:
            writer.writerow([r["hex"], r["callsign"], r["baro_altitude"], r["velocity"], r["timestamp"], r["muster"]])

    def render_main(self, params):
        rad = params.get('radius', ['5'])[0]
        alt = params.get('altfilter', ['all'])[0]
        df = params.get('date', [''])[0]
        q = 'SELECT callsign, baro_altitude, velocity, timestamp, muster FROM flugdaten'
        c = []
        if alt != 'all':
            c.append(f'baro_altitude<{int(alt)}')
        if df:
            d0 = datetime.fromisoformat(df)
            start = int(d0.timestamp())
            end = int(d0.replace(hour=23, minute=59, second=59).timestamp())
            c.append(f'timestamp BETWEEN {start} AND {end}')
        if c:
            q += ' WHERE ' + ' AND '.join(c)
        q += ' ORDER BY timestamp DESC LIMIT 100'
        rows_str = ''
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        for r in db.execute(q):
            dt = datetime.utcfromtimestamp(r['timestamp'])
            alt_class = 'low' if r['baro_altitude'] < 3000 else 'mid' if r['baro_altitude'] < 5000 else 'high'
            rows_str += f"<tr><td>{html.escape(r['callsign'] or '')}</td><td class='{alt_class}'>{r['baro_altitude']:.0f}</td><td>{r['velocity']:.0f}</td><td>{html.escape(r['muster'] or 'Unbekannt')}</td><td>{dt.strftime('%H:%M:%S')}</td><td>{dt.date()}</td></tr>"
        return MAIN_TEMPLATE.substitute(
            version=VERSION,
            radius=rad,
            altall='selected' if alt == 'all' else '',
            alt3000='selected' if alt == '3000' else '',
            alt5000='selected' if alt == '5000' else '',
            date=df,
            rows=rows_str,
            lat=EDTW_LAT,
            lon=EDTW_LON,
            radius_m=int(float(rad) * 1852)
        )

    def do_GET(self):
        if self.path == '/api/flights':
            con = sqlite3.connect(DB_PATH)
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            rows = cur.execute("SELECT callsign, baro_altitude, velocity, timestamp, muster, lat, lon FROM flugdaten ORDER BY timestamp DESC LIMIT 50").fetchall()
            con.close()
            result = [dict(r) for r in rows if r['lat'] is not None and r['lon'] is not None]
            data = json.dumps(result, ensure_ascii=False)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(data.encode('utf-8'))
            return
        p = urlparse(self.path)
        qs = parse_qs(p.query)
        if p.path == '/':
            out = self.render_main(qs).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        elif p.path == '/log':
            c = '\n'.join(log_lines[-50:])
            out = LOG_TEMPLATE.substitute(content=c).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        elif p.path == '/stats':
            con = sqlite3.connect(DB_PATH)
            cnt, last = con.execute('SELECT COUNT(*), MAX(timestamp) FROM flugdaten').fetchone()
            lf = datetime.utcfromtimestamp(last).strftime('%Y-%m-%d %H:%M UTC') if last else '–'
            out = STATS_TEMPLATE.substitute(count=cnt, latest=lf).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        elif p.path == '/reset':
            con = sqlite3.connect(DB_PATH)
            con.execute('DELETE FROM flugdaten')
            con.commit()
            con.close()
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
        elif p.path == '/update_muster':
            update_aircraft_db()
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
        elif p.path == '/export.csv':
            self.export_csv()
        else:
            self.send_error(404)

if __name__ == '__main__':
    init_db()
    update_aircraft_db()
    aircraft_db = load_aircraft_db()
    threading.Thread(target=fetch_and_store, daemon=True).start()
    print(f"[INFO] Starte Flugtracker v{VERSION} auf Port {PORT}...")
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("[INFO] Beende Flugtracker sauber...")
            httpd.server_close()
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] Serverfehler: {e}")
            httpd.server_close()
            sys.exit(1)
        except KeyboardInterrupt:
            print("[INFO] Beende Server...")
            httpd.server_close()
            sys.exit(0)
        except KeyboardInterrupt:
            print("[INFO] Beende Server...")
            httpd.server_close()
            sys.exit(0)
        except KeyboardInterrupt:
            print("[INFO] Beende Server...")
            httpd.server_close()
            sys.exit(0)
        except KeyboardInterrupt:
            print("\n[INFO] Beende Server...")
            httpd.server_close()
            sys.exit(0)

