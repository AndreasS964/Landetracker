# Flighttracker v1.7

Ein lokaler Flugtracker für ADS-B-Daten auf Raspberry Pi mit Web-Frontend, Kartenansicht und SQLite-Datenbank.

## Features

- Datenquelle: lokal (readsb) + optional OpenSky
- Speicherung in SQLite inkl. Koordinaten
- Web-Frontend mit Bootstrap + Leaflet
- Platzrunde als Polygon eingeblendet (EDTW)
- Filterbar nach Höhe, Datum, Radius
- API-Endpoint mit Filteroptionen (`/api/flights`)
- Datenexport als CSV/JSON (`/export`)
- Live-Refresh alle 60 Sekunden
- Logging in Datei mit Rotation
- Automatischer Daten-Cleanup nach 180 Tagen

## Dateien

- `flighttracker.py` – Hauptprogramm
- `platzrunde.gpx` – Platzrunde GPX-Datei
- `aircraft_db.csv` – wird automatisch geladen
- `tracker.log` – Logdatei

## Start

```bash
python3 flighttracker.py
```

Weboberfläche erreichbar unter: [http://localhost:8083](http://localhost:8083)

## Voraussetzungen

- Python 3
- `readsb` unter `http://127.0.0.1:8080/data.json`
- Optional: `tar1090`, `graphs1090` lokal verfügbar

## Lizenz

MIT License
