#!/bin/bash

echo "[*] Installation Flugtracker v1.5"

# Systemupdate & Grundpakete
sudo apt update
sudo apt install -y python3 python3-pip sqlite3

# Python-Abhängigkeiten
pip3 install -r requirements.txt

echo "[*] Installation abgeschlossen."
echo "[*] Starte mit: python3 flugtracker.py"
