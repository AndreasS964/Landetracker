#!/bin/bash
echo "📦 Starte vollständige Installation für Flighttracker v1.9h"

# --- System-Update und Essentials ---
echo "🔧 Pakete installieren..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-full python3-venv build-essential pkg-config curl                     libzstd-dev librtlsdr-dev rtl-sdr libusb-1.0-0-dev sqlite3

# --- RTL2832 DVB-T Treiber blockieren, damit SDR funktioniert ---
echo "⚙️ DVB-T Treiber blockieren (falls aktiv)..."
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtl.conf
sudo modprobe -r dvb_usb_rtl28xxu || true

# --- readsb installieren ---
echo "📡 Installiere readsb..."
sudo bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"

# --- Git Projekt holen (wenn nicht vorhanden) ---
if [ ! -d "Landetracker" ]; then
  echo "📥 Lade Projekt von GitHub..."
  git clone https://github.com/AndreasS964/Landetracker.git
fi
cd Landetracker || exit 1

# --- Python Umgebung einrichten ---
echo "🐍 Erstelle virtuelle Umgebung..."
python3 -m venv venv-tracker
source venv-tracker/bin/activate
pip install --upgrade pip
pip install requests

# --- Fertig ---
echo "✅ Installation abgeschlossen!"
echo "👉 Starte mit: source venv-tracker/bin/activate && python3 flighttracker.py"
