#!/bin/bash

INSTALL_DIR="/opt/flugtracker"
DB_PATH="/var/lib/flugtracker/flugdaten.db"
PORT=8083
ip=$(hostname -I | awk '{print $1}')

echo -e "\n🛠️ Flugtracker Systemcheck (v1.9e)"

# Dienststatus
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
[ -f "$INSTALL_DIR/aircraft_db.csv" ] && echo "📦 aircraft_db.csv vorhanden: ✅ OK" || echo "📦 aircraft_db.csv vorhanden: ⚠️ fehlt"

# Datenbank
if test -f "$DB_PATH"; then
  echo "📈 Datenbank existiert: ✅ OK"
else
  echo "📈 Datenbank existiert: ❌ NICHT vorhanden"
fi

# Port 8083 offen?
if ss -tulpen | grep -q ":$PORT"; then
  echo "🔌 Port $PORT offen (ss): ✅ JA"
else
  echo "🔌 Port $PORT offen (ss): ❌ NEIN"
fi

# Webserver-Port antwortet?
if curl -s --max-time 2 http://localhost:$PORT | grep -q '<html'; then
  echo "🌐 Webserver-Port $PORT erreichbar: ✅ OK"
else
  echo "🌐 Webserver-Port $PORT erreichbar: ❌ BLOCKIERT"
fi

# Optional: /flights.json verfügbar?
if curl -s http://localhost:$PORT/flights.json | grep -q 'callsign'; then
  echo "📦 Flugdaten abrufbar (/flights.json): ✅ OK"
else
  echo "📦 Flugdaten abrufbar (/flights.json): ⚠️ leer oder nicht erreichbar"
fi

echo -e "🌍 Weboberfläche erreichbar unter: http://$ip:$PORT"
echo "✅ Systemprüfung abgeschlossen."
