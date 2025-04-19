# 🛫 Flighttracker v1.7 – mit *readsb*, *tar1090* & *graphs1090*

Ein vollständiger ADS-B Flugtracker für Raspberry Pi – verarbeitet lokale Daten (via readsb), speichert sie in SQLite und zeigt sie über ein Webinterface an. Zusätzlich: Karten (tar1090) & Statistiken (graphs1090).

---

## ✨ Features
- 📡 ADS-B Datenempfang via RTL-SDR
- 🗃️ Lokale SQLite-Datenbank
- 🧭 Weboberfläche mit Karte, Filter, Log
- 🔄 Live-Daten + Verlauf
- 📤 Export: CSV & JSON
- 🛩️ Platzrunde via GPX-Datei (optional)

---

## ⚙️ Voraussetzungen
- Raspberry Pi mit Raspberry Pi OS (*Bookworm oder neuer*)
- RTL-SDR USB-Stick
- Python 3.11 + `python3-full`
- Internetzugang

---

## 🚀 Installation
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker
sudo apt install -y python3-full libzstd-dev
bash install_flighttracker.sh
```

---

## 🧪 Nutzung
```bash
source venv-tracker/bin/activate
python3 flighttracker.py
```

🔗 Öffne im Browser:  
[http://<Raspi-IP>:8083](http://<Raspi-IP>:8083)

---

## 🗺️ Platzrunde anzeigen (optional)
- Lege `platzrunde.gpx` ins Hauptverzeichnis.
- Wird automatisch im Interface geladen.

---

## 🔌 Datenquellen
- readsb (lokal, Beast-Port 30005)
- OpenSky Network (optional)

---

## 🔧 Wartung & Logs
- 📄 Logfile: `tracker.log`
- 🔁 Restart `readsb`:
```bash
sudo systemctl restart readsb
```
- 🛠️ Autostart: Optional via systemd-Service

---

## ⚠️ Bekannte Probleme
- `python3-full` **muss** installiert sein
- Bei Build-Fehlern (zstd):  
  → `sudo apt install libzstd-dev`
- Port 8080 oft deaktiviert → nur Port 30005 nutzen

---

## 🛠️ Ausblick v1.8
- Systemd-Service für Tracker
- Platzrunde editierbar (GPX-Editor)
- Performance-Optimierung
- Exportfilter nach Zeitraum & ICAO

---

## 💬 Support
👉 [GitHub Issues öffnen](https://github.com/AndreasS964/Landetracker/issues)

---

© 2025 AndreasS964 · MIT-Lizenz