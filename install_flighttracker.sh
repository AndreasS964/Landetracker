#!/bin/bash

# install_flighttracker.sh v1.9.1
# - sicher mit lighttpd-Konfig-Erweiterung
# - HTML-Statusausgabe nach /flugtracker/status.html
# - Update-kompatibel: kann bestehende Installation aktualisieren
# - optional interaktive Benutzerabfragen

set -euo pipefail

# Root-Check
if [ "$EUID" -ne 0 ]; then
  echo "\n❌ Bitte als root ausführen."
  exit 1
fi

# Parameter
INSTALL_DIR="/opt/flugtracker"
DB_DIR="/var/lib/flugtracker"
LOG_DIR="/var/log/flugtracker"
WWW_DIR="/var/www/html/flugtracker"
DEBUG_LOG="$LOG_DIR/debug.log"
DB_FILE="$DB_DIR/flugdaten.db"
PY_SCRIPT="flighttracker.py"
WEB_HTML="index.html"

# Interaktive Abfrage
read -p "🛠️ Neuinstallation (n) oder Update (u)? [n/u]: " MODE

if [[ "$MODE" == "n" ]]; then
  echo "📦 Führe Neuinstallation durch..."
  rm -rf "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"
  mkdir -p "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"
  touch "$DEBUG_LOG"
else
  echo "🔁 Update-Modus – vorhandene Daten bleiben erhalten."
  mkdir -p "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"
fi

chown -R www-data:www-data "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"

# Abhängigkeiten
apt update
apt install -y git lighttpd sqlite3 python3 python3-pip curl unzip

# readsb installieren
[ ! -x /usr/local/bin/readsb ] && bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"

# tar1090 & graphs1090
[ ! -f "/usr/local/share/tar1090/html/index.html" ] && bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/tar1090/master/install.sh)"
[ ! -f "/usr/local/share/graphs1090/html/index.html" ] && bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/graphs1090/master/install.sh)"

# Datei-Kopien
cp ./$PY_SCRIPT "$INSTALL_DIR/" || { echo "❌ $PY_SCRIPT fehlt"; exit 1; }
[ -f "./logo.png" ] && cp ./logo.png "$INSTALL_DIR/"
[ -f "./platzrunde.gpx" ] && cp ./platzrunde.gpx "$INSTALL_DIR/"
[ -f "./$WEB_HTML" ] && cp ./$WEB_HTML "$WWW_DIR/"
ln -sf "$DEBUG_LOG" "$WWW_DIR/tracker.log"

# Python-Abhängigkeiten
[ -f "./requirements.txt" ] && pip3 install --break-system-packages -r ./requirements.txt

# aircraft_db.csv vorbereiten
if [ ! -f "$INSTALL_DIR/aircraft_db.csv" ]; then
  if [ -f "./aircraftDatabase.csv" ]; then
    awk -F, 'NR==1 {for (i=1;i<=NF;i++) if ($i ~ /icao24/) c1=i; else if ($i ~ /typecode/) c2=i} NR>1 && $c1 && $c2 {gsub(/\'\'/,"",$c1); gsub(/\'\'/,"",$c2); print $c1 "," $c2}' ./aircraftDatabase.csv > "$INSTALL_DIR/aircraft_db.csv"
  elif [ -f "./aircraft_db.csv" ]; then
    cp ./aircraft_db.csv "$INSTALL_DIR/"
  else
    echo "icao,model" > "$INSTALL_DIR/aircraft_db.csv"
  fi
fi

# Datenbank anlegen (nur bei Neuinstallation)
if [[ "$MODE" == "n" && ! -f "$DB_FILE" ]]; then
  sqlite3 "$DB_FILE" <<EOF
CREATE TABLE IF NOT EXISTS flugdaten (
  hex TEXT, callsign TEXT, baro_altitude REAL, velocity REAL,
  timestamp INTEGER, muster TEXT, lat REAL, lon REAL
);
EOF
fi

# systemd-Dienst
cat > /etc/systemd/system/flugtracker.service <<EOF
[Unit]
Description=Flugtracker Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 $INSTALL_DIR/$PY_SCRIPT
WorkingDirectory=$INSTALL_DIR
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reexec
systemctl enable --now flugtracker.service

# lighttpd-Konfig sicher einbinden
echo 'server.modules += ("mod_alias")
alias.url += ("/flugtracker/" => "'$WWW_DIR'/")' > /etc/lighttpd/conf-available/99-flugtracker.conf
lighttpd-enable-mod 99-flugtracker || true
systemctl restart lighttpd

# Firewall
ufw allow 8083 || true
ufw reload || true

# HTML-Statusseite generieren
STATUS_FILE="$WWW_DIR/status.html"
echo "<html><body><h2>🛠️ Installation erfolgreich</h2><ul>" > "$STATUS_FILE"
echo "<li>Installationsmodus: $MODE</li>" >> "$STATUS_FILE"
echo "<li>Version: 1.9.1</li>" >> "$STATUS_FILE"
echo "<li>Webinterface: <a href='/flugtracker/'>/flugtracker/</a></li>" >> "$STATUS_FILE"
echo "<li>Dienststatus: \$(systemctl is-active flugtracker)</li>" >> "$STATUS_FILE"
echo "</ul></body></html>" >> "$STATUS_FILE"

echo "✅ Flugtracker fertig unter http://<IP>:8083"
echo "✅ Webinterface unter http://<IP>/flugtracker/"
echo "📄 Statusseite: http://<IP>/flugtracker/status.html"
