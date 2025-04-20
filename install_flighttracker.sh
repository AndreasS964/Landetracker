#!/bin/bash

echo "📦 Starte vollständige Installation für Flighttracker v1.7"

# Systempakete installieren
echo "🔧 Pakete installieren..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-full python3-venv python3-pip build-essential pkg-config curl \
                    rtl-sdr librtlsdr-dev sqlite3 lighttpd

# Blockiere Kernel-Modul für DVB-T
sudo bash -c 'echo "blacklist dvb_usb_rtl28xxu" > /etc/modprobe.d/blacklist-rtl.conf'
sudo modprobe -r dvb_usb_rtl28xxu || true

# readsb installieren (falls nicht vorhanden)
if ! [ -x "$(command -v readsb)" ]; then
  echo "📡 Installiere readsb..."
  sudo bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"
fi

# Projektverzeichnis vorbereiten
cd ~/Landetracker || { echo "❌ Landetracker-Verzeichnis fehlt!"; exit 1; }

# Python-Venv einrichten
echo "🐍 Python-Umgebung einrichten..."
python3 -m venv venv-tracker
source venv-tracker/bin/activate
pip install -r requirements.txt || pip install requests

# Systemd-Dienst anlegen
echo "🚀 Autostart-Dienst für Flighttracker einrichten..."
sudo tee /etc/systemd/system/flighttracker.service >/dev/null <<EOF
[Unit]
Description=Flighttracker v1.7
After=network.target

[Service]
ExecStart=/home/pi/Landetracker/venv-tracker/bin/python3 /home/pi/Landetracker/flighttracker.py
WorkingDirectory=/home/pi/Landetracker
StandardOutput=journal
StandardError=journal
Restart=always
RestartSec=10
User=pi
Environment="PYTHONUNBUFFERED=1"
WatchdogSec=60
NotifyAccess=all
Type=simple

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable flighttracker.service

# Lighttpd-Konfiguration prüfen und HTML bereitstellen
echo "🌐 Lighttpd-Webzugriff konfigurieren..."
sudo mkdir -p /var/www/html
sudo cp -f index.html /var/www/html/
sudo cp -f logo.png /var/www/html/
sudo chown www-data:www-data /var/www/html/index.html /var/www/html/logo.png
sudo chmod 644 /var/www/html/index.html /var/www/html/logo.png
sudo systemctl restart lighttpd
echo "✅ Webfrontend erreichbar unter: http://<IP>/index.html"

echo "✅ Installation abgeschlossen!"
echo "👉 Starte mit: source venv-tracker/bin/activate && python3 flighttracker.py"
