#!/bin/bash

echo "📦 Starte vollständige Installation für Flighttracker v1.9h"

echo "🔧 Pakete installieren..."
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3-full python3-venv build-essential pkg-config curl \
libzstd-dev librtlsdr-dev rtl-sdr libusb-1.0-0-dev sqlite3

echo "⚙️ DVB-T Treiber blockieren (falls aktiv)..."
echo "blacklist dvb_usb_rtl28xxu" | sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf
sudo rmmod dvb_usb_rtl28xxu 2>/dev/null || true

echo "📡 Installiere readsb..."
bash <(curl -s https://raw.githubusercontent.com/wiedehopf/adsb-scripts/master/readsb-install.sh)

echo "🗺️ Installiere tar1090..."
bash <(curl -s https://raw.githubusercontent.com/wiedehopf/tar1090/master/install.sh)

echo "📊 Installiere graphs1090..."
bash <(curl -s https://raw.githubusercontent.com/wiedehopf/graphs1090/master/install.sh)

echo "📥 Lade Projekt von GitHub..."
cd ~
rm -rf Landetracker
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker

echo "🐍 Erstelle virtuelle Umgebung..."
python3 -m venv venv-tracker
source venv-tracker/bin/activate
pip install --upgrade pip
pip install requests

echo "✅ Installation abgeschlossen!"
echo "👉 Starte mit: source venv-tracker/bin/activate && python3 flighttracker.py"

echo "🚀 Autostart-Dienst für Flighttracker einrichten..."

cat <<EOF | sudo tee /etc/systemd/system/flighttracker.service >/dev/null
[Unit]
Description=Flighttracker Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/pi/Landetracker
ExecStart=/home/pi/Landetracker/venv-tracker/bin/python3 /home/pi/Landetracker/flighttracker.py
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable flighttracker.service
sudo systemctl restart flighttracker.service
echo "✅ Autostart-Dienst eingerichtet!"

echo "🌐 Lighttpd-Konfiguration prüfen/anpassen..."

# Backup der bestehenden Config
if [ -f /etc/lighttpd/lighttpd.conf ]; then
    sudo cp /etc/lighttpd/lighttpd.conf /etc/lighttpd/lighttpd.conf.bak
fi

# Alias ergänzen (wenn nicht schon vorhanden)
if ! grep -q "landetracker" /etc/lighttpd/lighttpd.conf; then
    cat <<EOL | sudo tee -a /etc/lighttpd/lighttpd.conf >/dev/null

server.modules += ( "mod_alias", "mod_redirect", "mod_access" )

alias.url += ( "/landetracker" => "/home/pi/Landetracker/web" )

\$HTTP["url"] =~ "^/landetracker" {
    dir-listing.activate = "enable"
    url.access-deny = ( )
}
EOL
fi

# Konfiguration testen
sudo lighttpd -tt && sudo systemctl restart lighttpd && echo "✅ Lighttpd läuft mit Web-Zugriff auf /landetracker" || echo "❌ Lighttpd-Konfiguration fehlerhaft!"
