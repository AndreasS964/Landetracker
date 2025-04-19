#!/bin/bash

set -e

PORT=8083
LAT=48.27889122038788
LON=8.42936618151063

echo "📦 Starte vollständige Installation für Flighttracker v1.7"

# Pakete installieren
echo "🔧 Pakete installieren..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-full python3-venv build-essential pkg-config curl libzstd-dev \
                     libusb-1.0-0-dev librtlsdr-dev rtl-sdr sqlite3

# readsb installieren via wiedehopf-Script
echo "📡 Installiere readsb..."
sudo bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"

# Position festlegen
echo "📍 Setze Position: $LAT, $LON"
sudo sed -i "s/^LAT=.*/LAT=$LAT/" /etc/default/readsb || true
sudo sed -i "s/^LONG=.*/LONG=$LON/" /etc/default/readsb || true
sudo systemctl restart readsb

# Projektordner vorbereiten
cd ~
if [ ! -d "Landetracker" ]; then
  git clone https://github.com/AndreasS964/Landetracker.git
fi
cd Landetracker

# Python-Venv vorbereiten
python3 -m venv venv-tracker
source venv-tracker/bin/activate
pip install --upgrade pip
pip install requests

# Platzrunde.gpx sicherstellen
if [ ! -f platzrunde.gpx ]; then
  echo "⚠️  platzrunde.gpx nicht gefunden – bitte manuell hinzufügen."
fi

# Abschluss
echo "✅ Installation abgeschlossen!"
echo "👉 Starte mit: source venv-tracker/bin/activate && python3 flighttracker.py"
