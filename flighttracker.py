# flighttracker_stats_html.py – aktualisierte Version mit Chart.js-Statistikseite unter /stats und abgeschwächter Muster-Filter für adsb.lol

import http.server
import builtins
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
from collections import deque

PORT = 8083
DB_PATH = '/var/lib/flugtracker/flugdaten.db'
EDTW_LAT = 48.27889122038788
EDTW_LON = 8.42936618151063

log_lines = deque(maxlen=1000)
logger = logging.getLogger("tracker")
logger.setLevel(logging.INFO)
fh = RotatingFileHandler("/var/log/flugtracker/tracker.log", maxBytes=2_000_000, backupCount=3)
fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
wh = logging.StreamHandler()
wh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(fh)
logger.addHandler(wh)

class WebLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        log_lines.append(msg)
logger.addHandler(WebLogHandler())

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 0.539957

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
        if parsed.path == "/flights.json":
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute("SELECT * FROM flugdaten ORDER BY timestamp DESC LIMIT 500")
                    daten = []
                    for row in cursor.fetchall():
                        d = dict(row)
                        if d.get("lat") and d.get("lon"):
                            d["dist"] = round(haversine(d["lat"], d["lon"], EDTW_LAT, EDTW_LON), 2)
                        daten.append(d)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(daten).encode("utf-8"))
            except Exception as e:
                logger.error(f"Fehler bei flights.json: {e}")
                self.send_error(500, str(e))
        elif parsed.path == "/export.csv":
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute("SELECT * FROM flugdaten ORDER BY timestamp DESC LIMIT 500")
                    daten = [dict(row) for row in cursor.fetchall()]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv")
                    self.send_header("Content-Disposition", "attachment; filename=flugdaten.csv")
                    self.end_headers()
                    writer = csv.DictWriter(self.wfile, fieldnames=daten[0].keys())
                    writer.writeheader()
                    writer.writerows(daten)
            except Exception as e:
                logger.error(f"Fehler bei CSV-Export: {e}")
                self.send_error(500, str(e))
        elif parsed.path == "/log":
            content = '<html><head><meta charset="utf-8"><title>Log</title></head><body><h2>Log</h2><pre>'
            content += '<br>'.join(html.escape(l) for l in list(log_lines)[-100:])
            content += '</pre><a href="/">Zurück</a></body></html>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        elif parsed.path == "/api/adsb":
            fetch_adsblol()
            self.send_response(200)
            self.end_headers()
        elif parsed.path == "/stats":
            try:
                with open("stats.html", "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except Exception as e:
                logger.error(f"Fehler beim Laden von stats.html: {e}")
                self.send_error(500, str(e))
        elif parsed.path == "/stats.json":
            stats = fetch_stats()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode("utf-8"))
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

def cleanup_old_data():
    while True:
        try:
            cutoff = int(time.time()) - 180 * 86400
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute('DELETE FROM flugdaten WHERE timestamp < ?', (cutoff,))
                conn.commit()
            logger.info("Datenbereinigung abgeschlossen.")
        except Exception as e:
            logger.error(f"Fehler bei Datenbereinigung: {e}")
        time.sleep(86400)

def fetch_adsblol():
    try:
        logger.info("adsb.lol-Datenabruf gestartet...")
        url = f"https://api.adsb.lol/v2/lat/{EDTW_LAT}/lon/{EDTW_LON}/dist/25"
        r = requests.get(url, timeout=10)
        if r.ok:
            data = r.json().get("aircraft", [])
            count = 0
            with sqlite3.connect(DB_PATH) as conn:
                for f in data:
                    if not f.get("hex") or not f.get("lat") or not f.get("lon"):
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
                    if not flight["muster"]:
                        flight["muster"] = "?"
                    try:
                        logger.debug(f"Speichere Flug: {flight}")
                        conn.execute('''INSERT INTO flugdaten (hex, callsign, baro_altitude, velocity, timestamp, muster, lat, lon)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                     (flight["hex"], flight["callsign"], flight["baro_altitude"], flight["velocity"],
                                      flight["timestamp"], flight["muster"], flight["lat"], flight["lon"]))
                        count += 1
                    except Exception as e:
                        logger.warning(f"Eintrag übersprungen: {e}")
                conn.commit()
            logger.info(f"{count} Flugdaten gespeichert.")
        else:
            logger.warning(f"adsb.lol-Antwort: {r.status_code}")
    except Exception as e:
        logger.error(f"Fehler bei adsb.lol-Abruf: {e}")

def adsblol_loop():
    while True:
        try:
            fetch_adsblol()
        except Exception as e:
            logger.warning(f"adsblol_loop-Fehler: {e}")
        time.sleep(300)

AIRCRAFT_CSV = 'aircraft_db.csv'
READSB_DB_PATH = "/run/readsb/aircraft.json"

def load_aircraft_db():
    db = {}
    try:
        with open(AIRCRAFT_CSV, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                db[r['icao'].strip().upper()] = r['model'].strip()
        logger.info(f"Musterliste geladen: {len(db)} Typen")
    except Exception as e:
        logger.warning("aircraft_db.csv nicht gefunden – nutze nur readsb.")
    return db

def load_readsb_db():
    try:
        with open(READSB_DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"readsb aircraft.json nicht gefunden oder fehlerhaft: {e}")
        return {}

def bestimme_muster(flight, readsb_db, aircraft_db):
    icao = flight.get("hex", "").upper()
    typ = ""
    if icao in readsb_db and isinstance(readsb_db[icao], dict):
        typ = readsb_db[icao].get("type", "").strip().upper()
    if not typ:
        typ = flight.get("type", "").strip().upper()
    return aircraft_db.get(typ, typ if typ else icao)

def watchdog_loop():
    while True:
        try:
            import systemd.daemon
            systemd.daemon.notify("WATCHDOG=1")
        except: pass
        time.sleep(60)

if __name__ == '__main__':
    logger.info(f"Starte Flugtracker auf Port {PORT}...")
    print(f"✅ Flugtracker läuft auf Port {PORT}")
    try:
        aircraft_db = load_aircraft_db()
        readsb_db = load_readsb_db()

        with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
            threading.Thread(target=cleanup_old_data, daemon=True).start()
            threading.Thread(target=adsblol_loop, daemon=True).start()
            threading.Thread(target=watchdog_loop, daemon=True).start()
            httpd.serve_forever()
    except Exception as e:
        logger.critical(f"HTTP-Server abgestürzt: {e}")
