#!/bin/bash

# Flugtracker Installer v1.7
# Installiert readsb, 1090tar, SQLite, Web-Frontend mit Karte und Statistik, sowie cronjob für Datenbereinigung
# Zielplattform: Raspberry Pi mit Raspbian/Debian-basiertem System

set -e

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
  echo "Installing readsb..."
  git clone https://github.com/wiedehopf/readsb.git /tmp/readsb
  cd /tmp/readsb
  make -j3
  make install
  mkdir -p /etc/readsb
  cp /tmp/readsb/debian/readsb.default /etc/default/readsb || true
  cp /tmp/readsb/debian/readsb.service /etc/systemd/system/readsb.service
  systemctl enable readsb
  systemctl start readsb
else
  echo "readsb bereits installiert, Installation wird übersprungen."
fi

# RTL-Treiber blockieren (falls SDR verwendet wird)
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf

# tar1090 & graphs1090 installieren (optional)
echo "Installiere tar1090 & graphs1090..."
bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/tar1090/master/install.sh)"
bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/graphs1090/master/install.sh)"

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

# Datenbank vorbereiten
if [ ! -f "$DB_DIR/flights.db" ]; then
  echo "Creating initial SQLite DB..."
  python3 scripts/init_db.py "$DB_DIR/flights.db"
fi

# Web-Dateien kopieren
cp -r web/* "$WWW_DIR"

# Neue index.html bereitstellen
cat <<EOF > "$WWW_DIR/index.html"
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Flugtracker</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>Flugtracker</h1>
    <p>Live-Daten, Statistiken & Platzrunde</p>
  </header>
  <main>
    <div id="map"></div>
    <section id="stats"></section>
    <section id="filters"></section>
    <section id="table"></section>
  </main>
  <footer>
    <p>Version 1.7 – &copy; Flugtracker</p>
  </footer>
  <script src="leaflet.js"></script>
  <script src="main.js"></script>
</body>
</html>
EOF

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

echo "Installation abgeschlossen. Webinterface unter http://<IP-Adresse>/ erreichbar."
