#!/bin/bash

echo "📦 Starte vollständige Installation für Flighttracker v1.7"

# System aktualisieren und Pakete installieren
echo "🔧 Pakete installieren..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-full python3-venv python3-pip     sqlite3 rtl-sdr build-essential pkg-config libusb-1.0-0-dev librtlsdr-dev     curl libzstd-dev

# Projektverzeichnis vorbereiten
cd ~/ || exit
rm -rf Landetracker
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker || exit

# Python venv einrichten
echo "🐍 Python-Venv vorbereiten..."
python3 -m venv venv-tracker
source venv-tracker/bin/activate
pip install --upgrade pip
pip install pyModeS

# Datenbank initialisieren
echo "📁 Datenbank initialisieren..."
[ ! -f tracker.db ] && sqlite3 tracker.db < init.sql

# readsb installieren (nur Beast-Modus)
echo "🛠️ Installiere readsb (nur Beast-Port)..."
cd ~
rm -rf readsb
git clone https://github.com/wiedehopf/readsb.git
cd readsb || exit
make -j$(nproc)
sudo cp readsb /usr/bin/readsb

# readsb systemd service
echo "📄 Setze readsb systemd-Service..."
sudo tee /etc/systemd/system/readsb.service > /dev/null <<EOF
[Unit]
Description=readsb ADS-B Empfänger
After=network.target
[Service]
ExecStart=/usr/bin/readsb --device 0 --device-type rtlsdr --gain auto --ppm 0 --lat 48.2789 --lon 8.4293 --write-json /run/readsb --json-location-accuracy --net --net-beast --net-ro-port 30005
Restart=always
User=root
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable readsb
sudo systemctl start readsb

# tar1090 installieren
echo "🗺️ Installiere tar1090..."
sudo bash -c "$(wget -qO - https://github.com/wiedehopf/tar1090/raw/master/install.sh)"

# graphs1090 installieren
echo "📊 Installiere graphs1090..."
sudo bash -c "$(wget -qO - https://github.com/wiedehopf/graphs1090/raw/master/install.sh)"

echo "✅ Installation abgeschlossen!"
echo "👉 Starte mit: source venv-tracker/bin/activate && python3 flighttracker.py"