#!/bin/bash
echo "🛠️ Flugtracker Systemcheck (v1.8)"

echo -n "🔍 Flighttracker-Dienst läuft: "
pgrep -f flighttracker.py >/dev/null && echo "✅ OK" || echo "❌ NICHT gestartet"

echo -n "📡 readsb-Dienst aktiv: "
systemctl is-active --quiet readsb && echo "✅ OK" || echo "❌ NICHT aktiv"

echo -n "🛩️ JSON-Daten vorhanden (readsb): "
[ -f /run/readsb/aircraft.json ] && echo "✅ OK" || echo "❌ NICHT gefunden"

echo -n "📁 platzrunde.gpx vorhanden: "
[ -f platzrunde.gpx ] && echo "✅ OK" || echo "⚠️ fehlt"

echo -n "🖼️ logo.png vorhanden: "
[ -f logo.png ] && echo "✅ OK" || echo "⚠️ fehlt"

echo -n "📈 Datenbank existiert: "
[ -f flugdaten.db ] && echo "✅ OK" || echo "❌ NICHT vorhanden"

echo -n "🕒 DuckDNS Cronjob vorhanden: "
crontab -l 2>/dev/null | grep -q duckdns/duck.sh && echo "✅ OK" || echo "⚠️ NICHT eingerichtet"

echo -n "🌐 Port 8083 erreichbar: "
nc -z localhost 8083 && echo "✅ OK" || echo "❌ BLOCKIERT"

echo "✅ Systemprüfung abgeschlossen."
