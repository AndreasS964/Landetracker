![Flugtracker Logo](flugtracker_logo_final.png)

# 🛩️ Flugtracker v1.9f

## 🔧 Funktionen

- 📡 Empfängt Flugdaten über `readsb` oder OpenSky API
- 💾 Speichert Flugdaten lokal in SQLite
- 🗺️ Zeigt Flugbewegungen auf Leaflet-Karte
- 📈 Tabelle mit Filter- und Sortierfunktionen
- 🛬 Bewegungsart-Erkennung (Anflug / Abflug)
- 🧭 Platzrunde über `platzrunde.gpx`
- 📊 Statistiken: Landungen pro Tag (30 Tage)
- 📁 CSV-Export der Tabelle
- 🌐 OpenSky-Abruf (Platzhalter vorbereitet)
- 🚀 Manueller Datenabruf mit „DB-Aktualisieren“-Button
- ⏳ Zeitfilter mit Datum oder Dropdown
- 🧭 Filter nach Callsign, Höhe, Radius, Bewegungsart
- 📌 Zeigt standardmäßig letzte 7 Tage

## 📂 Dateien

- `flighttracker.py` – Hauptserver mit SQLite, REST, Logging
- `index.html` – Weboberfläche (ohne Flask, rein HTML/JS)
- `platzrunde.gpx` – Platzrundenpfad für Leaflet
- `aircraft_db.csv` – Typenliste (automatischer Abruf)

## 🧭 Bewegungsart-Logik

Jeder Flugdatensatz enthält:

- `"arrival"` → Höhe < 2200 ft & Abstand < 3 NM
- `"departure"` → Höhe > 3200 ft & Abstand < 3 NM
- `""` → wenn nicht eindeutig

Frontend-Filterbar über Dropdown.

## 🖱️ Web-Oberfläche

| Button              | Funktion                                      |
|---------------------|-----------------------------------------------|
| 🔄 Anzeigen         | Lädt und filtert Daten                        |
| 📁 CSV              | Exportiert aktuelle Tabelle als CSV           |
| 🌐 OpenSky          | Platzhalter (für geplante Anbindung)          |
| 🚀 DB-Aktualisieren | Führt sofort Datenabruf via /refresh-now aus |

## ⚙️ Installation

```bash
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker
bash install_flighttracker.sh
source venv-tracker/bin/activate
python3 flighttracker.py
```

## 👤 Version

**v1.9f** – entwickelt für Flugleiter und Platzüberwachung  
**by Andreas Sika**