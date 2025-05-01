#!/bin/bash

# install_flighttracker.sh
# Flugtracker Installer v1.7 (aktualisiert)
# Installiert readsb, tar1090, graphs1090, Web-Frontend, Datenbank, Autostart und Debug-Logging

set -euo pipefail

# Parameter
INSTALL_DIR="/opt/flugtracker"
DB_DIR="/var/lib/flugtracker"
LOG_DIR="/var/log/flugtracker"
WWW_DIR="/var/www/html/flugtracker"
CRON_FILE="/etc/cron.d/flugtracker_cleanup"
DEBUG_LOG="/var/log/flugtracker/debug.log"
ENABLE_DEBUG=true

# Abhängigkeiten
apt update
apt remove -y lighttpd || true
apt install -y git nginx sqlite3 python3 python3-pip curl unzip

# readsb installieren (nur wenn NICHT bereits installiert)
if [ ! -x /usr/local/bin/readsb ]; then
  echo "Installing readsb über wiedehopf-Skript..."
  bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"
else
  echo "readsb bereits installiert, Installation wird übersprungen."
fi

# RTL-Treiber blockieren (falls SDR verwendet wird)
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf

# tar1090 & graphs1090 installieren
echo "Installiere tar1090 & graphs1090..."
bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/tar1090/master/install.sh)"
bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/graphs1090/master/install.sh)"

# Firewall freigeben (wenn ufw installiert ist)
if command -v ufw &>/dev/null; then
  ufw allow 80/tcp || true
fi

# Verzeichnisse anlegen
mkdir -p "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"
touch "$DEBUG_LOG"
chown -R www-data:www

# Weiterleitungsseite für Port 80 erstellen
cat <<EOF > /var/www/html/index.html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=http://localhost:8083/">
  <title>Flugtracker Weiterleitung</title>
</head>
<body>
  <p>Weiterleitung zu <a href="http://localhost:8083/">Flugtracker Weboberfläche</a>...</p>
</body>
</html>
EOF


