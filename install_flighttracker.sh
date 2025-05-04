#!/bin/bash
# install_flighttracker.sh – Flugtracker Installer v1.9e
# by Andreas Sika

set -euo pipefail

### Root-Prüfung
if [ "$(id -u)" -ne 0 ]; then
  echo "❌ Dieses Skript muss mit Root-Rechten ausgeführt werden (z. B. über 'sudo -i')."
  exit 1
fi

### Konfiguration
INSTALL_DIR="/opt/flugtracker"
DB_DIR="/var/lib/flugtracker"
LOG_DIR="/var/log/flugtracker"
WWW_DIR="/var/www/html/flugtracker"
DEBUG_LOG="$LOG_DIR/debug.log"
CRON_FILE="/etc/cron.d/flugtracker_cleanup"
PORT=8083

echo "📦 Führe Neuinstallation durch..."

### Alte Installation optional löschen
read -rp "❓ Alte Installation löschen? (j/N): " confirm
if [[ "$confirm" =~ ^[Jj]$ ]]; then
  echo "🧹 Entferne alte Verzeichnisse..."
  rm -rf "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"
fi

### Abhängigkeiten
echo "🔧 Installiere Abhängigkeiten..."
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

### SDR blockieren
echo 'blacklist dvb_usb_rtl28xxu' > /etc/modprobe.d/rtl-sdr-blacklist.conf

### tar1090 / graphs1090
echo "📟 Installiere tar1090 & graphs1090..."
bash -c "$(wget -qO - https://raw.githubusercontent.com/wiedehopf/tar1090/master/install.sh)"
bash -c "$(wget -qO - https://raw.githubusercontent.com/wiedehopf/graphs1090/master/install.sh)"

### Webserver (lighttpd)
echo "🌐 Konfiguriere lighttpd..."
lighty-enable-mod fastcgi fastcgi-php || true
systemctl restart lighttpd

### Verzeichnisse
echo "📁 Erstelle Verzeichnisse..."
mkdir -p "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"
touch "$DEBUG_LOG"
chown -R www-data:www-data "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"

### Web-Dateien
echo "🌍 Kopiere Web-Dateien..."
cp -v index.html platzrunde.gpx logo.png "$WWW_DIR" 2>/dev/null || echo "⚠️ Einige Web-Dateien fehlen – bitte manuell kopieren"

### Python-Umgebung
echo "🐍 Richte Python-Umgebung ein..."
python3 -m venv venv-tracker
source venv-tracker/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || echo "⚠️ requirements.txt nicht gefunden oder leer"

### Cronjob: automatische DB-Bereinigung
echo "🧹 Plane Datenbereinigung via Cron (180 Tage)..."
cat <<EOF > "$CRON_FILE"
0 4 * * * root sqlite3 $DB_DIR/flugdaten.db "DELETE FROM flugdaten WHERE timestamp < strftime('%s','now','-180 days');"
EOF

### Abschluss
echo "✅ Installation abgeschlossen!"
echo "👉 Starte Flugtracker mit:"
echo "   source venv-tracker/bin/activate && python3 flighttracker.py"
echo "🌍 Webinterface erreichbar unter: http://<IP>:$PORT"

### Automatischer Systemcheck
echo ""
echo "🔍 Führe Systemcheck durch..."
bash ./check_system.sh || echo "⚠️ check_system.sh fehlgeschlagen oder nicht vorhanden."
