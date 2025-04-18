# Landetracker (Flugplatz EDTW)

Ein platznaher Flugtracker basierend auf ADS-B, kombiniert aus OpenSky und lokalem readsb-Feed (z. B. via tar1090).

## Version 1.6 – Highlights
- ✔️ gleichzeitige Nutzung von OpenSky API & readsb JSON
- ✔️ automatische ICAO-Muster-Zuordnung
- ✔️ farbige Höhenanzeige (<3000/5000/5000+ ft)
- ✔️ Leaflet-Karte mit Radiusdarstellung um EDTW
- ✔️ moderne Bootstrap-Oberfläche
- ✔️ Dublettenfilterung pro Zeitstempel & Hex
- ✔️ Logging, Statistik, Reset-Button

## Setup auf Raspberry Pi
```bash
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker
bash install_tracker.sh
python3 flugtracker.py


## Voraussetzungen
- Python 3
- `readsb` & `tar1090` manuell installiert
- Internetzugang für OpenSky + Flugzeugdatenbank

---

# Landetracker (EN)

Simple local flight tracker (e.g. for 5nm radius around EDTW), using OpenSky ADS-B data.

## Features
- Web interface with filters (altitude, date, radius)
- ICAO model lookup
- Logging + stats
- Local port 8083

## Setup (Raspberry Pi)
1. `git clone https://github.com/AndreasS964/Landetracker.git`
2. `cd Landetracker`
3. `bash install_tracker.sh`
4. `python3 flugtracker.py`

## Requirements
- Python 3
- `readsb` & `tar1090` manually installed
- Internet access for OpenSky and aircraft DB
