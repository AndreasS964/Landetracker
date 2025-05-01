#!/bin/bash

INSTALL_DIR="/opt/flugtracker"
DB_PATH="/var/lib/flugtracker/flights.db"
PORT=80
ip=$(hostname -I | awk '{print $1}')

echo "🛠️ Flugtracker Systemcheck (v1.9e)"

# systemd-Dienst prüfen
if systemctl is-active --quiet flugtracker; then
  echo "🔍 Flighttracker-Dienst läuft: ✅ OK"
else
  echo "🔍 Flighttracker-Dienst läuft: ❌ NICHT gestartet"
fi

# readsb aktiv?
if systemctl is-active --quiet readsb; then
  echo "📡 readsb-Dienst aktiv: ✅ OK"
else
  echo "📡 readsb-Dienst aktiv: ❌ NICHT gefunden"
fi

# JSON-Daten
if curl -s http://localhost/data/aircraft.json | grep -q 'hex'; then
  echo "🛩️ JSON-Daten vorhanden (readsb): ✅ OK"
else
  echo "🛩️ JSON-Daten vorhanden (readsb): ❌ FEHLEN"
fi

# Platzrunde & Logo
[ -f "$INSTALL_DIR/platzrunde.gpx" ] && echo "📁 platzrunde.gpx vorhanden: ✅ OK" || echo "📁 platzrunde.gpx vorhanden: ⚠️ fehlt"
[ -f "$INSTALL_DIR/logo.png" ] && echo "🖼️ logo.png vorhanden: ✅ OK" || echo "🖼️ logo.png vorhanden: ⚠️ fehlt"

# DB
if sudo test -f "$DB_PATH"; then
  echo "📈 Datenbank existiert: ✅ OK"
else
  echo "📈 Datenbank existiert: ❌ NICHT vorhanden"
fi

# Port erreichbar
if curl -s --max-time 2 http://localhost:$PORT | grep -q '<html'; then
  echo "🌐 Webserver-Port $PORT erreichbar: ✅ OK"
else
  echo "🌐 Webserver-Port $PORT erreichbar: ❌ BLOCKIERT"
fi

echo "🌍 Weboberfläche: http://$ip (nginx-Port $PORT)"
echo "✅ Systemprüfung abgeschlossen."
