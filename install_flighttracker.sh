#!/bin/bash

echo "📦 Installation: Flighttracker v1.9e (saubere Neuinstallation)"
cd ~

# 🔥 Ordner entfernen
rm -rf ~/Landetracker

# 🧬 Neu klonen (ersetze ggf. URL)
git clone https://github.com/AndreasS964/Landetracker.git ~/Landetracker
cd ~/Landetracker
mkdir -p ~/Landetracker

# 🧰 Systempakete
sudo apt update
sudo apt install -y git python3 python3-pip rtl-sdr sqlite3 curl netcat-openbsd lighttpd

# 🧹 RTL-Treiber blockieren
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf

# 🐍 Python-Abhängigkeiten
pip3 install requests --break-system-packages

# 🛰 readsb installieren (falls nicht vorhanden)
if ! systemctl is-active --quiet readsb; then
  sudo bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"
fi

# 🧭 Platzrunde & Logo kopieren (optional)
cp platzrunde.gpx logo.png . 2>/dev/null || true

# 🔁 Autostart-Dienst
sudo tee /etc/systemd/system/flighttracker.service > /dev/null <<EOF
[Unit]
Description=Flighttracker Webserver
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/Landetracker/flighttracker.py
WorkingDirectory=/home/pi/Landetracker
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

# 🌐 Lighttpd Proxy für Portweiterleitung
sudo lighty-enable-mod proxy
sudo lighty-enable-mod proxy-http
sudo tee /etc/lighttpd/conf-available/88-flighttracker.conf > /dev/null <<EOF
server.modules += ( "mod_proxy", "mod_proxy_http" )
\$HTTP["url"] =~ "^/" {
  proxy.server = (
    "" => (
      "flighttracker" => (
        "host" => "127.0.0.1",
        "port" => 8083
      )
    )
  )
}
EOF
sudo lighty-enable-mod 88-flighttracker
sudo systemctl restart lighttpd

# ✅ Abschluss
echo "✅ Installation abgeschlossen"
echo "📡 Starte jetzt manuell: python3 ~/Landetracker/flighttracker.py"
echo "🌍 Weboberfläche unter: http://<pi-ip>:8083 oder via Lighttpd"

# 🧪 Systemprüfung
bash ~/Landetracker/check_system.sh

