# Flighttracker v1.7 mit readsb, tar1090 und graphs1090

Ein vollständiger ADS-B Flugtracker für Raspberry Pi, der lokale Daten (via readsb) verarbeitet, speichert und über eine Weboberfläche anzeigt. Zusätzlich werden tar1090 und graphs1090 installiert.

## Features
- ADS-B Datenempfang via RTL-SDR
- Lokale SQLite-Datenbank
- Weboberfläche mit Filter, Karte und Log
- Platzrunde (GPX-Overlay möglich)
- Datenexport (CSV, JSON)
- Live-Daten und Verlauf

## Voraussetzungen
- Raspberry Pi mit Raspberry Pi OS (Bookworm oder höher)
- Internetverbindung
- RTL-SDR USB-Stick
- Python 3.11 mit `python3-full`

## Installation
```bash
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker
sudo apt update && sudo apt upgrade -y
sudo apt install python3-full libzstd-dev -y
bash install_flighttracker.sh
```

## Nutzung
```bash
source venv-tracker/bin/activate
python3 flighttracker.py
```
Öffne danach im Browser: [http://<Raspi-IP>:8083](http://<Raspi-IP>:8083)

## Konfiguration
- Standort in `install_flighttracker.sh` anpassen (`--lat`, `--lon`)
- Platzrunde (optional): `platzrunde.gpx` in Hauptverzeichnis legen

## Platzrunde
Um eine lokale Platzrunde (z. B. für EDTW) anzuzeigen:
- Datei `platzrunde.gpx` mit Geokoordinaten im Hauptverzeichnis ablegen
- Diese wird automatisch im Karteninterface eingeblendet (falls verfügbar)

## Datenquellen
- **readsb** (lokal, Beast-Modus Port 30005)
- **OpenSky Network** (optional, manuell abrufbar)

## Logs & Wartung
- Log: `tracker.log`
- Neustart von readsb:
```bash
sudo systemctl restart readsb
```
- Tracker bei Start automatisch starten? Systemd-Service optional möglich

## Bekannte Probleme
- Python 3.11 auf Raspberry Pi OS Bookworm benötigt venv wegen PEP 668
- Port 8080 ist bei readsb oft nicht aktiviert → nur Beast-Port genutzt
- Bei Pip-Fehlern: Installation bricht ab, wenn kein `python3-full` installiert ist
- Bei Build-Fehlern (zstd.h fehlt): Paket `libzstd-dev` installieren:
```bash
sudo apt install libzstd-dev
```

## Nächste Schritte (v1.8 geplant)
- Eigener systemd-Service für Tracker
- Platzrunde im GPX-Editor anpassbar
- Performance-Optimierungen bei vielen Flugzeugen
- Exportfilter für CSV/JSON

## Support
Für Fragen: [GitHub Issues öffnen](https://github.com/AndreasS964/Landetracker/issues)

---
© 2025 AndreasS964 – Open Source unter MIT-Lizenz
