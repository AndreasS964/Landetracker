#!/bin/bash

echo "📦 Starte Installation für Flighttracker v1.8 (clean Pi Setup)"
cd ~

echo "🔧 Systempakete installieren..."
sudo apt update
sudo apt install -y git python3 python3-pip rtl-sdr sqlite3 curl netcat

echo "🧹 RTL-Treiber blockieren..."
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf

echo "📁 Flighttracker-Ordner vorbereiten..."
rm -rf ~/Landetracker
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker

echo "🐍 Python-Abhängigkeiten installieren (systemweit)..."
pip3 install requests --break-system-packages

echo "📄 index.html aktualisieren..."
wget -q -O index.html https://raw.githubusercontent.com/AndreasS964/Landetracker/main/index.html

echo "📡 readsb installieren..."
sudo bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"

echo "🛰️ DuckDNS vorbereiten..."
mkdir -p ~/duckdns
echo '#!/bin/bash' > ~/duckdns/duck.sh
echo 'echo url="https://www.duckdns.org/update?domains=andreassika&token=89d793ae-f4a3-486f-ad52-7475986679af&ip=" | curl -k -o ~/duckdns/duck.log -K -' >> ~/duckdns/duck.sh
chmod 700 ~/duckdns/duck.sh
(crontab -l 2>/dev/null; echo "*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1") | crontab -

echo "📁 Platzrunde & Logo sichern (falls vorhanden)..."
cp platzrunde.gpx logo.png . 2>/dev/null || true

echo "🔁 Autostart-Dienst einrichten..."
cat <<EOF | sudo tee /etc/systemd/system/flighttracker.service
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

echo "✅ Installation abgeschlossen!"
echo "👉 Starte manuell mit: python3 ~/Landetracker/flighttracker.py"

echo "🌐 Lighttpd-Reverse-Proxy einrichten..."
sudo apt install -y lighttpd
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