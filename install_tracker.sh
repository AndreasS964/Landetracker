#!/bin/bash

echo "[*] Installation Flugtracker v1.6 (mit virtualenv)"

# Systemupdate & Tools
sudo apt update
sudo apt install -y python3 python3-pip python3-venv sqlite3 git

# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install --upgrade pip
pip install -r requirements.txt

echo "[*] Installation abgeschlossen."
echo
echo "Starte mit:"
echo "  source venv/bin/activate"
echo "  python flugtracker.py"
