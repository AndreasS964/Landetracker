#!/bin/bash

echo "📦 Starte vollständige Installation für Flighttracker v1.7"

# Systemabhängige Pakete
echo "🔧 Pakete installieren..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-full python3-venv python3-pip sqlite3                     rtl-sdr build-essential pkg-config libusb-1.0-0-dev                     librtlsdr-dev curl libzstd-dev

# Virtuelle Umgebung vorbereiten
echo "🐍 Python-Venv vorbereiten..."
python3 -m venv venv-tracker
source venv-tracker/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Datenbank vorbereiten
echo "📁 Datenbank initialisieren..."
sqlite3 flights.db < init.sql

# readsb Installation (Beast Input only)
echo "🛠️ Installiere readsb (nur Beast-Port)..."
sudo apt install -y libncurses-dev
git clone https://github.com/wiedehopf/readsb.git
cd readsb
make -j2 || true
sudo cp readsb /usr/local/bin/readsb || echo "⚠️ Build fehlgeschlagen."
cd ..

# tar1090 Installation
echo "🗺️ Installiere tar1090..."
curl -sSL https://github.com/wiedehopf/tar1090/raw/master/install.sh | sudo bash

# graphs1090 Installation
echo "📊 Installiere graphs1090..."
curl -sSL https://github.com/wiedehopf/graphs1090/raw/master/install.sh | sudo bash

echo "✅ Installation abgeschlossen!"
echo "👉 Starte mit: source venv-tracker/bin/activate && python3 flighttracker.py"