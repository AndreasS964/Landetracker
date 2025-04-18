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

# HTML Template mit Bootstrap, Farben, Karte & Links zu tar1090/graphs1090
MAIN_TEMPLATE = Template(r"""... (bleibt unverändert) ...""")

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
        elif p.path == '/export.csv':
            self.export_csv()
        else:
            self.send_error(404)

if __name__ == '__main__':
    print(f"[INFO] Starte Flugtracker v{VERSION} auf Port {PORT}...")
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Beende Server...")
            httpd.server_close()
            sys.exit(0)
