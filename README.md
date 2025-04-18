# Landetracker (Flugplatz EDTW)

Ein leichter Flugtracker zur Platzüberwachung (z. B. 5nm Radius um EDTW), basierend auf ADS-B-Daten der OpenSky API.

## Funktionen
- Web-UI mit Filter (Höhe, Radius, Datum)
- automatische ICAO-Muster-Zuordnung
- Logging + Statistiken
- lokal laufend auf Port 8083

## Setup (Raspberry Pi)
1. `git clone https://github.com/AndreasS964/Landetracker.git`
2. `cd Landetracker`
3. `bash install_tracker.sh`
4. `python3 flugtracker.py`

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
