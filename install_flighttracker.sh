#!/bin/bash

echo "📦 Starte vollständige Installation für Flighttracker v1.8"
cd ~

echo "🔧 Benötigte Pakete installieren..."
sudo apt update
sudo apt install -y git python3-full python3-venv python3-pip rtl-sdr sqlite3 unzip curl

echo "🧹 Eventuell blockierende RTL-Treiber deaktivieren..."
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf

echo "📦 Flighttracker aus GitHub klonen..."
rm -rf ~/Landetracker
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker

echo "🐍 Python-Umgebung einrichten..."
python3 -m venv venv-tracker
source venv-tracker/bin/activate
pip install --upgrade pip
pip install requests

echo "📡 readsb installieren..."
sudo bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"

echo "🔁 Platzrunde und Logo kopieren (falls vorhanden)..."
cp platzrunde.gpx logo.png . 2>/dev/null || true

echo "🔁 Systemd-Dienst für Autostart einrichten..."
cat <<EOF | sudo tee /etc/systemd/system/flighttracker.service
[Unit]
Description=Flighttracker Webserver
After=network.target

[Service]
ExecStart=$(pwd)/venv-tracker/bin/python3 $(pwd)/flighttracker.py
WorkingDirectory=$(pwd)
Restart=always
User=pi
WatchdogSec=60
Type=simple
NotifyAccess=all

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable flighttracker.service

echo "✅ Installation abgeschlossen!"
echo "👉 Starte mit: source venv-tracker/bin/activate && python3 flighttracker.py"
