# 🛩️ Flugtracker v1.9b – Andreas Sika

## 🔧 Funktionen

- 📡 Empfängt Flugdaten über `readsb` oder OpenSky API
- 💾 Speichert Flugdaten lokal in SQLite
- 🗺️ Zeigt Live-Flugbewegungen in Leaflet-Karte
- 📈 Tabellenansicht mit Filter- und Sortierfunktionen
- 🛬 Bewegungsart-Erkennung (Anflug / Abflug)
- 🧭 Anzeige der Platzrunde (`platzrunde.gpx`)
- 📊 Statistikseite: Landungen pro Tag
- 📁 CSV-Export der angezeigten Flüge
- 🌐 OpenSky-Abruf vorbereitet
- 🔃 Manuelles Aktualisieren & Zeitfilter
- 📌 Anzeige letzter 7 Tage (standard)

## 📂 Dateien

- `flighttracker.py` – Hauptserver, Datenverarbeitung und API
- `index.html` – Weboberfläche (keine Flask, reines HTML/JS)
- `platzrunde.gpx` – Platzrunde als GPX-Datei
- `aircraft_db.csv` – Typendatenbank (wird automatisch geladen)

## 🧭 Bewegungsart-Logik (mode)

Jeder Flugdatenpunkt wird wie folgt bewertet:

- **Anflug (`arrival`)**:  
  Höhe < 1200 ft **und** Position < 1 NM vom Platz

- **Abflug (`departure`)**:  
  Höhe > 3000 ft **und** Position < 1 NM vom Platz

→ Wird im Feld `mode` gespeichert und ist im Frontend filterbar.

## 🖱️ Web-Buttons

- 🔁 `Anzeigen`: Daten neu laden
- ⏳ `Zeitraum`: Schnellfilter (Heute / 7 Tage etc.)
- 🚁 `Bewegungsart`: Anflug / Abflug selektieren
- 🌐 `OpenSky`: vorbereitet für API-Abruf
- 📁 `CSV`: exportiert sichtbare Tabelle

## ⚙️ Installation

```bash
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker
bash install_flighttracker.sh
source venv-tracker/bin/activate
python3 flighttracker.py
```

## 👤 Version

**v1.9b** – entwickelt für Flugleiter & Platzüberwachung  
**by Andreas Sika**