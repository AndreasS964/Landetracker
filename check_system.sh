#!/bin/bash

echo "🛠️ Flugtracker Systemcheck (v1.9e)"

echo -n "🔍 Flighttracker-Dienst läuft: "
systemctl is-active --quiet flighttracker && echo "✅ OK" || echo "❌ NICHT gestartet"

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

echo -n "🌐 Webserver-Port 8083 erreichbar: "
nc -z localhost 8083 && echo "✅ OK" || echo "❌ BLOCKIERT"

IP=$(hostname -I | awk '{print $1}')
echo "🌍 Weboberfläche: http://$IP:8083 oder via Lighttpd"

echo "✅ Systemprüfung abgeschlossen."
