#!/bin/bash

set -e

echo "📦 Starte vollständige Installation für Flighttracker v1.7"

echo "🔧 Systempakete installieren..."
sudo apt update
sudo apt install -y git python3 python3-venv sqlite3 rtl-sdr build-essential pkg-config libusb-1.0-0-dev librtlsdr-dev curl

echo "🐍 Python-Venv vorbereiten..."
python3 -m venv ~/Landetracker/venv-tracker
source ~/Landetracker/venv-tracker/bin/activate
pip install --upgrade pip
pip install pyModeS flask

echo "📥 Landetracker Repo holen..."
cd ~
rm -rf Landetracker_tmp
git clone https://github.com/AndreasS964/Landetracker.git Landetracker_tmp
cp -r Landetracker_tmp/* ~/Landetracker/
rm -rf Landetracker_tmp

echo "📁 Datenbank initialisieren..."
~/Landetracker/venv-tracker/bin/python3 -c "import flighttracker; flighttracker.init_db()"

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

echo "📊 tar1090 und graphs1090 installieren..."
sudo bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/adsb-scripts/master/tar1090-install.sh)"
sudo bash -c "$(wget -q -O - https://raw.githubusercontent.com/wiedehopf/adsb-scripts/master/graphs1090-install.sh)"

echo "🚀 Starte Flighttracker (im Hintergrund)..."
cd ~/Landetracker
nohup ~/Landetracker/venv-tracker/bin/python3 flighttracker.py > tracker.out 2>&1 &

echo ""
echo "✅ Installation abgeschlossen!"
echo "🌐 Webinterface unter: http://<PI-IP>:8083"
echo "📊 tar1090: http://<PI-IP>/tar1090"
echo "📈 graphs1090: http://<PI-IP>/graphs1090"
