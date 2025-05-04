#!/bin/bash

# Hinweis bei Start über sudo ohne TTY
export TERM=${TERM:-xterm}  # Setze TERM für dialog-Nutzung

# Arbeitsverzeichnis prüfen
if [[ ! -f "./install_flighttracker.sh" || ! -f "./flighttracker.py" ]]; then
  echo "❌ Bitte aus dem Landetracker-Verzeichnis aufrufen (z. B. /home/pi/Landetracker)"
  exit 1
fi
if [ -z "$(tty)" ] || [ ! -t 0 ]; then
  echo "❌ Dieses Skript muss in einem interaktiven Terminal ausgeführt werden."
  echo "🔧 Lösung: Starte es z. B. mit: sudo -i && ./install_flighttracker.sh"
  exit 1
fi

set -euo pipefail

# Parameter
INSTALL_DIR="/opt/flugtracker"
DB_DIR="/var/lib/flugtracker"
LOG_DIR="/var/log/flugtracker"
WWW_DIR="/var/www/html/flugtracker"
DEBUG_LOG="$LOG_DIR/debug.log"
DB_FILE="$DB_DIR/flugdaten.db"
PY_SCRIPT="flighttracker.py"
WEB_HTML="index.html"

# dialog prüfen
if ! command -v dialog &> /dev/null; then
  apt install -y dialog
fi

# Installationsmodus auswählen
if command -v dialog &>/dev/null; then
  MODE=$(dialog --clear --stdout --title "Installationsmodus" \
    --menu "Wähle den Modus:" 15 50 3 \
    n "Neuinstallation (löscht alles)" \
    u "Update (Daten bleiben erhalten)" \
    c "Custom (Komponenten wählen)")
else
  echo "⚠️ dialog nicht verfügbar – Textmodus aktiviert"
  read -rp "Installationsmodus wählen (n/u/c): " MODE
fi

if [[ -z "${MODE:-}" ]]; then
  echo "❌ Kein Installationsmodus gewählt – Abbruch."
  exit 1
fi
fi

# Custom-Auswahl
if [[ "$MODE" == "c" ]]; then
  CHOICES=$(dialog --checklist "Komponenten auswählen" 20 60 10 \
    1 "readsb installieren" on \
    2 "tar1090/graphs1090 installieren" on \
    3 "lighttpd konfigurieren" on \
    4 "Python-Abhängigkeiten" on \
    5 "flighttracker.py kopieren" on \
    --stdout)
  [[ "$CHOICES" =~ 1 ]] && INSTALL_READSB="y"
  [[ "$CHOICES" =~ 2 ]] && INSTALL_TAR="y"
  [[ "$CHOICES" =~ 3 ]] && CONFIG_LIGHTTPD="y"
  [[ "$CHOICES" =~ 4 ]] && INSTALL_PY="y"
  [[ "$CHOICES" =~ 5 ]] && COPY_PY="y"
fi

# Verzeichnisse vorbereiten
if [[ "$MODE" == "n" ]]; then
  echo "📦 Führe Neuinstallation durch..."
  rm -rf "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"
fi
mkdir -p "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"
touch "$DEBUG_LOG"
chown -R www-data:www-data "$INSTALL_DIR" "$DB_DIR" "$LOG_DIR" "$WWW_DIR"

# Abhängigkeiten
apt update && apt install -y git lighttpd sqlite3 python3 python3-pip curl unzip

# readsb installieren
if [[ "$MODE" != "c" || "${INSTALL_READSB:-}" =~ ^[Yy]$ ]]; then
  [ ! -x /usr/local/bin/readsb ] && bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"
fi

# tar1090 & graphs1090
if [[ "$MODE" != "c" || "${INSTALL_TAR:-}" =~ ^[Yy]$ ]]; then
  [ ! -f "/usr/local/share/tar1090/html/index.html" ] && bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/tar1090/master/install.sh)"
  [ ! -f "/usr/local/share/graphs1090/html/index.html" ] && bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/graphs1090/master/install.sh)"
fi

# Datei-Kopien
if [[ "$MODE" != "c" || "${COPY_PY:-}" =~ ^[Yy]$ ]]; then
  cp ./$PY_SCRIPT "$INSTALL_DIR/" || { echo "❌ $PY_SCRIPT fehlt"; exit 1; }
fi
[ -f "./logo.png" ] && cp ./logo.png "$INSTALL_DIR/"
[ -f "./platzrunde.gpx" ] && cp ./platzrunde.gpx "$INSTALL_DIR/"
[ -f "./$WEB_HTML" ] && cp ./$WEB_HTML "$WWW_DIR/"
ln -sf "$DEBUG_LOG" "$WWW_DIR/tracker.log"

# Python-Abhängigkeiten
if [[ "$MODE" != "c" || "${INSTALL_PY:-}" =~ ^[Yy]$ ]]; then
  [ -f "./requirements.txt" ] && pip3 install --break-system-packages -r ./requirements.txt
fi

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
if [[ "$MODE" != "c" || "${CONFIG_LIGHTTPD:-}" =~ ^[Yy]$ ]]; then
  echo 'server.modules += ("mod_alias")
alias.url += ("/flugtracker/" => "'$WWW_DIR'/")' > /etc/lighttpd/conf-available/99-flugtracker.conf
  lighttpd-enable-mod 99-flugtracker || true
  systemctl restart lighttpd
fi

# Firewall
if command -v ufw &> /dev/null; then
  ufw allow 8083 || true
  ufw reload || true
else
  echo "⚠️ ufw nicht installiert – Firewall-Regel übersprungen."
fi

# HTML-Statusseite generieren
STATUS_FILE="$WWW_DIR/status.html"
echo "<html><body><h2>🛠️ Installation erfolgreich</h2><ul>" > "$STATUS_FILE"
echo "<li>Installationsmodus: $MODE</li>" >> "$STATUS_FILE"
echo "<li>Version: 1.9.1</li>" >> "$STATUS_FILE"
echo "<li>Webinterface: <a href='/flugtracker/'>/flugtracker/</a></li>" >> "$STATUS_FILE"
echo "<li>Dienststatus: $(systemctl is-active flugtracker)</li>" >> "$STATUS_FILE"
echo "</ul></body></html>" >> "$STATUS_FILE"

echo "✅ Flugtracker fertig unter http://<IP>:8083"
echo "✅ Webinterface unter http://<IP>/flugtracker/"
echo "📄 Statusseite: http://<IP>/flugtracker/status.html"

read -p "Drücke Enter zum Beenden..."

