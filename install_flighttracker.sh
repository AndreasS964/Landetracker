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
apt remove -y lighttpd nginx || true
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
  echo "
