#!/bin/bash
# install_flighttracker.sh – Flugtracker Installer v1.9e
# Setzt readsb, tar1090, graphs1090, Web-Frontend, SQLite-DB, Logging & Autostart auf

set -euo pipefail

### Konfiguration
INSTALL_DIR="/opt/flugtracker"
DB_DIR="/var/lib/flugtracker"
LOG_DIR="/var/log/flugtracker"
WWW_DIR="/var/www/html/flugtracker"
CRON_FILE="/etc/cron.d/flugtracker_cleanup"
DEBUG_LOG="$LOG_DIR/debug.log"
PORT=8083

echo "🚀 Starte Flugtracker-Installation (lighttpd-Version)..."

### Abhängigkeiten
echo "📦 Installiere Abhängigkeiten..."
apt update
apt remove -y nginx || true
apt install -y git lighttpd sqlite3 python3 python3-pip curl unzip

### readsb nur installieren, wenn nicht vorhanden
if ! command -v readsb &>/dev/null; then
  echo "📡 Installing readsb..."
  bash -c "$(wget -qO - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"
else
  echo "📡 readsb bereits vorhanden."
fi

### SDR-Treiber blockieren
echo 'blacklist dvb_usb_rtl28xxu' > /etc/modprobe.d/rtl-sdr-blacklist.conf

### tar1090 & graphs1090
echo "📟 Installiere tar1090 & graphs1090..."
bash -c "$(wget -qO - https://raw.githubusercontent.com/wiedehopf/tar1090/master/install.sh)"
bash -c "$(wget -qO - https://raw.githubusercontent.com/wiedehopf/graphs1090/master/install.sh)"

### lighttpd konfigurieren
echo "🌐 Konfiguriere lighttpd..."
lighty-enable-mod fastcgi fastcgi-php || true
systemctl restart lighttpd

### Verzeichnisse und Rechte
echo "📁 Erstelle Verzeichnisse..."
mkdir -p "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"
touch "$DEBUG_LOG"
chown -R www-data:www-data "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"

### Web-Dateien kopieren
echo "📁 Kopiere Web-Frontend-Dateien..."
cp -v index.html platzrunde.gpx logo.png "$WWW_DIR" 2>/dev/null || echo "⚠️ Web-Dateien fehlen (werden ggf. später ergänzt)"

### Python-Umgebung
echo "🐍 Installiere Python-Abhängigkeiten..."
python3 -m venv venv-tracker
source venv-tracker/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || echo "⚠️ requirements.txt fehlt oder leer"

### Cleanup-Job
echo "🧹 Plane automatischen Daten-Cleanup (180 Tage)..."
cat <<EOF > "$CRON_FILE"
0 3 * * * root sqlite3 $DB_DIR/flugdaten.db "DELETE FROM flugdaten WHERE timestamp < strftime('%s','now','-180 days');"
EOF

### Abschluss
echo "✅ Installation abgeschlossen!"
echo "📌 Starte Flugtracker mit:"
echo "   source venv-tracker/bin/activate && python3 flighttracker.py"
echo "🌍 Web-Oberfläche: http://<IP>:$PORT"
