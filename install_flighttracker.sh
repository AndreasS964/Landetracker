#!/bin/bash
echo "📦 Starte vollständige Installation für Flighttracker v1.9h"

# --- System-Update und Essentials ---
echo "🔧 Pakete installieren..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-full python3-venv build-essential pkg-config curl \
                    libzstd-dev librtlsdr-dev rtl-sdr libusb-1.0-0-dev sqlite3

# --- RTL2832 DVB-T Treiber blockieren ---
echo "⚙️ DVB-T Treiber blockieren (falls aktiv)..."
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtl.conf
sudo modprobe -r dvb_usb_rtl28xxu || true

# --- readsb installieren ---
echo "📡 Installiere readsb..."
sudo bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"

# --- readsb.service ersetzen mit stabilem Setup ---
echo "📄 Ersetze systemd-Dienst für readsb..."
sudo tee /etc/systemd/system/readsb.service > /dev/null <<EOF
[Unit]
Description=readsb ADS-B Empfänger
After=network.target

[Service]
ExecStart=/usr/bin/readsb \
  --device 0 \
  --device-type rtlsdr \
  --gain auto \
  --lat 48.2789 \
  --lon 8.4293 \
  --write-json /run/readsb \
  --net \
  --net-ro-port 30005
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable readsb
sudo systemctl restart readsb

# --- graphs1090 installieren ---
echo "📊 Installiere graphs1090..."
sudo bash -c "$(wget -O - https://github.com/wiedehopf/graphs1090/raw/master/install.sh)"

# --- Projekt holen (falls nicht vorhanden) ---
if [ ! -d "Landetracker" ]; then
  echo "📥 Lade Projekt von GitHub..."
  git clone https://github.com/AndreasS964/Landetracker.git
fi
cd Landetracker || exit 1

# --- Python Umgebung vorbereiten ---
echo "🐍 Erstelle virtuelle Umgebung..."
python3 -m venv venv-tracker
source venv-tracker/bin/activate
pip install --upgrade pip
pip install requests

echo "✅ Installation abgeschlossen!"
echo "👉 Starte mit: source venv-tracker/bin/activate && python3 flighttracker.py"

# --- Autostart für Flighttracker einrichten ---
echo "🚀 Autostart-Dienst für Flighttracker einrichten..."
sudo tee /etc/systemd/system/flighttracker.service > /dev/null <<EOF
[Unit]
Description=Flighttracker Python Webserver
After=network.target

[Service]
WorkingDirectory=/home/pi/Landetracker
ExecStart=/home/pi/Landetracker/venv-tracker/bin/python3 /home/pi/Landetracker/flighttracker.py
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable flighttracker
