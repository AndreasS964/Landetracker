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
chown -R www-data:www-data "$DB_DIR" "$LOG_DIR" "$WWW_DIR" "$DEBUG_LOG"

# Tracker-Code installieren
echo "Installing Flugtracker..."
rm -rf "$INSTALL_DIR"
git clone https://github.com/deinname/flugtracker.git "$INSTALL_DIR"
cd "$INSTALL_DIR"
pip3 install -r requirements.txt

# Datenbank vorbereiten (Tracker legt DB beim ersten Start selbst an)
if [ ! -f "$DB_DIR/flights.db" ]; then
  echo "Lege leere SQLite-DB an (Tracker initialisiert sie beim Start)..."
  touch "$DB_DIR/flights.db"
  chown www-data:www-data "$DB_DIR/flights.db"
fi

# Web-Dateien kopieren
cp -r web/* "$WWW_DIR"
cp platzrunde.gpx logo.png "$WWW_DIR" 2>/dev/null || true

# nginx konfigurieren
cat <<EOF > /etc/nginx/sites-available/flugtracker
server {
    listen 80;
    server_name _;
    root $WWW_DIR;

    location / {
        index index.html;
        try_files \$uri \$uri/ =404;
    }
}
EOF
ln -sf /etc/nginx/sites-available/flugtracker /etc/nginx/sites-enabled/flugtracker
rm -f /etc/nginx/sites-enabled/default
systemctl reload nginx

# cronjob für DB-Cleanup
cat <<EOF > "$CRON_FILE"
0 3 * * * www-data sqlite3 $DB_DIR/flights.db "DELETE FROM flights WHERE timestamp < strftime('%s','now','-180 days');"
EOF
chmod 644 "$CRON_FILE"

# Startskript
cat <<EOF > /usr/local/bin/flugtracker-start
#!/bin/bash
cd "$INSTALL_DIR"
CMD="python3 tracker.py --db \"$DB_DIR/flights.db\" --log \"$LOG_DIR/tracker.log\""
# Falls Debuglog nicht schreibbar, umleiten auf /dev/null
if [ "$ENABLE_DEBUG" = true ] && [ -w "$DEBUG_LOG" ]; then
  CMD+=" --debug >> \"$DEBUG_LOG\" 2>&1"
elif [ "$ENABLE_DEBUG" = true ]; then
  CMD+=" --debug >> /dev/null 2>&1"
fi

eval $CMD
EOF
chmod +x /usr/local/bin/flugtracker-start

# Autostart mit systemd
cat <<EOF > /etc/systemd/system/flugtracker.service
[Unit]
Description=Flugtracker ADS-B Logger
After=network.target

[Service]
ExecStart=/usr/local/bin/flugtracker-start
Restart=always
User=www-data
ProtectSystem=full
ProtectHome=yes
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable flugtracker
systemctl start flugtracker

# Optionaler System-Check nach Installation
if [ -f "$INSTALL_DIR/scripts/check.sh" ]; then
  echo "Starte System-Check..."
  bash "$INSTALL_DIR/scripts/check.sh" || echo "Check meldet Probleme – bitte prüfen!"
else
  echo "Warnung: check.sh nicht gefunden, Systemtest wird übersprungen."
fi

echo "✅ Installation abgeschlossen. Webinterface unter http://<IP-Adresse>/ erreichbar."
