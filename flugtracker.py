...
# (Alles wie bisher)

# HTTP Handler
class Handler(http.server.BaseHTTPRequestHandler):
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
            c = sqlite3.connect(DB_PATH)
            c.execute('DELETE FROM flugdaten')
            c.commit()
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_error(404)

# Main Start
if __name__ == '__main__':
    init_db()
    update_aircraft_db()
    aircraft_db = load_aircraft_db()
    fetch_thread = threading.Thread(target=fetch_and_store, daemon=True)
    fetch_thread.start()
    threading.Thread(target=hw_watchdog, daemon=True).start()
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Server läuft auf Port {PORT}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            shutdown_event.set()
            sys.exit(0)
