#!/bin/bash

set -e

echo "📦 Starte vollständige Installation für Flighttracker v1.7"

echo "🔧 Pakete installieren..."
sudo apt update
sudo apt install -y git python3 python3-pip sqlite3 rtl-sdr build-essential pkg-config libusb-1.0-0-dev librtlsdr-dev

echo "🐍 Python-Abhängigkeiten installieren..."
pip3 install pyModeS flask

echo "📥 Flighttracker herunterladen..."
cd ~
rm -rf Landetracker
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker

echo "📁 Datenbank initialisieren..."
python3 -c "import flighttracker; flighttracker.init_db()"

echo "🛰 readsb neu bauen (Web & Beast-Modus)..."
cd ~
rm -rf readsb
git clone https://github.com/wiedehopf/readsb.git
cd readsb
make -j4
sudo cp readsb /usr/bin/readsb
sudo chmod +x /usr/bin/readsb

echo "⚙️ readsb systemd-Service konfigurieren..."
sudo mkdir -p /etc/systemd/system/readsb.service.d
cat <<EOF | sudo tee /etc/systemd/system/readsb.service.d/override.conf > /dev/null
[Service]
ExecStart=
ExecStart=/usr/bin/readsb --device-type rtlsdr --gain auto --ppm 0 --lat 48.2789 --lon 8.4293 --write-json /run/readsb --json-location-accuracy --net
EOF

sudo systemctl daemon-reload
sudo systemctl restart readsb

echo "📡 Starte Flighttracker direkt..."
cd ~/Landetracker
nohup python3 flighttracker.py > tracker.out 2>&1 &

echo "✅ Installation abgeschlossen!"
echo "🌐 Webinterface unter: http://<PI-IP>:8083"
