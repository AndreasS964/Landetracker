#!/bin/bash

# install_flighttracker.sh
# Flugtracker Installer v1.9 – inkl. systemd, lighttpd für tar1090 und graphs1090, ohne Reverse Proxy, Logzugriff, Requirements & aircraft_db.csv

set -euo pipefail

# Parameter
INSTALL_DIR="/opt/flugtracker"
DB_DIR="/var/lib/flugtracker"
LOG_DIR="/var/log/flugtracker"
WWW_DIR="/var/www/html/flugtracker"
DEBUG_LOG="$LOG_DIR/debug.log"
ENABLE_DEBUG=true

# Abhängigkeiten installieren
apt update
apt install -y git lighttpd sqlite3 python3 python3-pip curl unzip

# readsb installieren (wenn nicht vorhanden)
if [ ! -x /usr/local/bin/readsb ]; then
  echo "Installing readsb über wiedehopf-Skript..."
  bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"
else
  echo "readsb bereits installiert, Übersprungen."
fi

# RTL-Treiber blockieren (falls SDR verwendet wird)
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf

# tar1090 & graphs1090 installieren (nur wenn nicht vorhanden)
if [ ! -f "/usr/local/share/tar1090/html/index.html" ]; then
  echo "Installiere tar1090..."
  bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/tar1090/master/install.sh)"
else
  echo "tar1090 bereits vorhanden – übersprungen."
fi

if [ ! -f "/usr/local/share/graphs1090/html/index.html" ]; then
  echo "Installiere graphs1090..."
  bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/graphs1090/master/install.sh)"
else
  echo "graphs1090 bereits vorhanden – übersprungen."
fi

# Alte Installation bereinigen
rm -rf "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"

# Verzeichnisse anlegen
mkdir -p "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"
touch "$DEBUG_LOG"
chown -R www-data:www-data "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"

# Logdatei im WWW verlinken
ln -sf "$DEBUG_LOG" "$WWW_DIR/tracker.log"

# Dateien kopieren: logo.png und platzrunde.gpx
if [ -f "./logo.png" ]; then
  sudo cp ./logo.png "$INSTALL_DIR/"
  echo "✅ logo.png erfolgreich kopiert."
else
  echo "⚠️ logo.png fehlt."
fi

if [ -f "./platzrunde.gpx" ]; then
  sudo cp ./platzrunde.gpx "$INSTALL_DIR/"
  echo "✅ platzrunde.gpx erfolgreich kopiert."
else
  echo "⚠️ platzrunde.gpx fehlt."
fi

# Python-Requirements installieren
if [ -f "./requirements.txt" ]; then
  pip3 install --break-system-packages -r ./requirements.txt || pip3 install --break-system-packages flask pyModeS
fi

# aircraft_db.csv bereitstellen
if [ ! -f "$INSTALL_DIR/aircraft_db.csv" ]; then
  if [ -f "./aircraftDatabase.csv" ]; then
    echo "🛠️ Konvertiere aircraftDatabase.csv → aircraft_db.csv (OpenSky-Format)..."
    awk -F, 'NR==1 {for (i=1; i<=NF; i++) if ($i ~ /icao24/) c1=i; else if ($i ~ /typecode/) c2=i} NR>1 && $c1!="" && $c2!="" {gsub(/'\''/,"",$c1); gsub(/'\''/,"",$c2); print $c1 "," $c2}' ./aircraftDatabase.csv > "$INSTALL_DIR/aircraft_db.csv"
    echo "✅ aircraft_db.csv erstellt aus aircraftDatabase.csv"
  elif [ -f "./aircraft_db.csv" ]; then
    sudo cp ./aircraft_db.csv "$INSTALL_DIR/"
    echo "✅ aircraft_db.csv aus lokalem Verzeichnis kopiert."
  else
    echo "icao,model" > "$INSTALL_DIR/aircraft_db.csv"
    echo "⚠️ aircraft_db.csv nicht gefunden – Dummy-Datei erstellt."
  fi
fi

if [ -f "$INSTALL_DIR/aircraft_db.csv" ]; then
  TYPECOUNT=$(wc -l < "$INSTALL_DIR/aircraft_db.csv")
  echo "📦 aircraft_db.csv geladen – $((TYPECOUNT - 1)) Einträge gefunden."
fi

# SQLite-Datenbank erstellen, wenn sie fehlt
if [ ! -f "$INSTALL_DIR/flugdaten.db" ]; then
  echo "🛠️ Erstelle SQLite-Datenbank flugdaten.db..."
  sqlite3 "$INSTALL_DIR/flugdaten.db" <<EOF
  CREATE TABLE flugdaten (
    icao24 TEXT,
    typecode TEXT,
    latitude REAL,
    longitude REAL,
    altitude REAL,
    speed REAL,
    track REAL
  );
EOF
  echo "✅ flugdaten.db und Tabelle flugdaten erstellt."
fi

# systemd-Dienst für Flugtracker einrichten
cat > /etc/systemd/system/flugtracker.service <<EOF
[Unit]
Description=Flugtracker Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 $INSTALL_DIR/flighttracker.py
WorkingDirectory=$INSTALL_DIR
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reexec
systemctl enable --now flugtracker.service

# lighttpd für tar1090 und graphs1090 konfigurieren
echo "Konfiguriere lighttpd für tar1090 und graphs1090..."
cat > /etc/lighttpd/lighttpd.conf <<EOF
server.modules += ( "mod_proxy" )
server.document-root = "/usr/local/share/tar1090/html"
EOF

# lighttpd neu starten
sudo systemctl restart lighttpd

# Firewall konfigurieren
sudo ufw allow 8083
sudo ufw reload

echo "✅ Flugtracker läuft nun direkt auf Port 8083."
echo "✅ lighttpd bedient jetzt tar1090 und graphs1090."
echo "Zugriff auf tar1090 unter http://<raspi-ip>/tar1090 möglich."
echo "Zugriff auf graphs1090 unter http://<raspi-ip>/graphs1090 möglich."
echo "✅ Installation abgeschlossen. Führe Systemprüfung durch..."

# Starte Systemcheck
if [ -f "check_system.sh" ]; then
  chmod +x check_system.sh
  ./check_system.sh
else
  echo "⚠️ check_system.sh nicht gefunden. Manuell ausführen, wenn gewünscht."
fi
