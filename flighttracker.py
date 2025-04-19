# --- Main ---
if __name__ == '__main__':
    import mimetypes

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/log':
                log_html = '<br>'.join(str(line) for line in log_lines[-50:])
                content = f'<html><head><meta charset="utf-8"><title>Log</title></head><body><h2>Log</h2><pre>{log_html}</pre><a href="/">Zurück</a></body></html>'.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            elif self.path == '/' or self.path == '/index.html':
                try:
                    with open("index.html", "rb") as f:
                        content = f.read()
                        self.send_response(200)
                        self.send_header("Content-Type", mimetypes.guess_type("index.html")[0])
                        self.send_header("Content-Length", str(len(content)))
                        self.end_headers()
                        self.wfile.write(content)
                except FileNotFoundError:
                    self.send_error(404, "index.html nicht gefunden")
            elif self.path == '/flights.json':
                try:
                    cutoff = int(time.time()) - 300
                    with sqlite3.connect(DB_PATH) as conn:
                        rows = conn.execute("SELECT lat, lon, callsign, baro_altitude FROM flugdaten WHERE timestamp > ?", (cutoff,)).fetchall()
                    data = [{"lat": r[0], "lon": r[1], "cs": r[2], "alt": r[3]} for r in rows if r[0] and r[1]]
                    payload = json.dumps(data).encode('utf-8')
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except Exception as e:
                    logger.error(f"Fehler bei /flights.json: {e}")
                    self.send_error(500, "Fehler beim Abrufen der Flugdaten")
            else:
                self.send_error(404, "Nicht gefunden")

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