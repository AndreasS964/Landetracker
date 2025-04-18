#!/bin/bash

set -e

# Farben
GRUEN='\033[0;32m'
ROT='\033[0;31m'
NC='\033[0m' # Keine Farbe

echo -e "${GRUEN}📦 Starte vollständige Installation für Flighttracker v1.7${NC}"

# Systempakete
echo -e "${GRUEN}🔧 Pakete installieren...${NC}"
sudo apt update
sudo apt install -y git python3 python3-full python3-venv python3-pip sqlite3 rtl-sdr build-essential pkg-config libusb-1.0-0-dev librtlsdr-dev curl

# Python-Venv vorbereiten
echo -e "${GRUEN}🐍 Python-Venv vorbereiten...${NC}"
python3 -m venv venv-tracker
source venv-tracker/bin/activate
pip install --upgrade pip
pip install pyModeS flask

echo -e "${GRUEN}📥 Landetracker Repo holen...${NC}"
rm -rf Landetracker
mkdir -p Landetracker
cd Landetracker
cp ../flighttracker.py .
cp ../platzrunde.gpx . 2>/dev/null || true

# SQLite-DB initialisieren
echo -e "${GRUEN}📁 Datenbank initialisieren...${NC}"
if [ ! -f tracker.db ]; then
    echo "CREATE TABLE IF NOT EXISTS flights (icao TEXT, lat REAL, lon REAL, alt INTEGER, speed REAL, track REAL, seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP);" | sqlite3 tracker.db
fi

# readsb installieren (ohne JSON-Port)
echo -e "${GRUEN}🛠️ Installiere readsb (nur Beast-Port)...${NC}"
git clone https://github.com/wiedehopf/readsb.git
cd readsb
make -j4
sudo make install || true
cd ..

# readsb systemd override
echo -e "${GRUEN}⚙️ Konfiguriere readsb systemd-Service...${NC}"
sudo mkdir -p /etc/systemd/system/readsb.service.d
cat <<EOF | sudo tee /etc/systemd/system/readsb.service.d/override.conf > /dev/null
[Service]
ExecStart=
ExecStart=/usr/bin/readsb --device-type rtlsdr --gain auto --ppm 0 --lat 48.2789 --lon 8.4293 --write-json /run/readsb --quiet --net --beast --net-beast --net-beast-port 30005
EOF
sudo systemctl daemon-reload
sudo systemctl restart readsb

# tar1090 und graphs1090
echo -e "${GRUEN}🌐 Installiere tar1090 und graphs1090...${NC}"
bash <(wget -qO- https://github.com/wiedehopf/tar1090/raw/master/install.sh)
bash <(wget -qO- https://github.com/wiedehopf/graphs1090/raw/master/install.sh)

# Abschluss
echo -e "${GRUEN}✅ Installation abgeschlossen.${NC}"
echo -e "${GRUEN}📍 Tracker starten mit:${NC} source venv-tracker/bin/activate && python3 flighttracker.py"
echo -e "${GRUEN}🌍 Aufruf im Browser:${NC} http://<raspi-ip>:8083"
