# ✈️ Flighttracker v1.7

Ein lokaler ADS-B-Flugtracker mit Weboberfläche. Funktioniert ohne Internetzugang, basiert auf:

- 🛰 **readsb** (Beast TCP)
- 🐍 **Python 3** (pyModeS, sqlite3, http.server)
- 🌐 **Web-UI mit Leaflet**, Bootstrap & Karte
- 📁 Speicherung in SQLite-Datenbank
- 🗂 CSV-basierte Flugzeugdatenbank (ICAO → Muster)

---

## 📦 Voraussetzungen

- Raspberry Pi mit RTL-SDR Stick (z. B. NooElec)
- Debian/Ubuntu Linux mit Python 3.9+
- Internetzugang bei der ersten Installation (zum Download)

---

## ⚙️ Installation (Einzeiler)

```bash
wget https://raw.githubusercontent.com/AndreasS964/Landetracker/main/install_flighttracker.sh
chmod +x install_flighttracker.sh
./install_flighttracker.sh
```

---

## 🌐 Webinterface

Rufe im Browser auf:

```
http://<IP-des-Raspberry>:8083
```

---

## 🔁 Datenquellen

- ✅ Beast TCP Mode (Port 30005) über readsb
- 🔄 Platzrunde wird per GPX-Datei (`platzrunde.gpx`) angezeigt
- ❌ JSON-Fetch (Port 8080) ist deaktiviert

---

## 📂 Struktur

```
Landetracker/
├── flighttracker.py       # Hauptanwendung
├── flugdaten.db           # SQLite-Datenbank (automatisch)
├── aircraft_db.csv        # Musterliste ICAO → Modell
├── platzrunde.gpx         # Platzrunde als GPX-Track (optional)
├── tracker.log            # Logging
├── install_flighttracker.sh # Installer
```

---

## 🔧 Manuelle Steuerung

```bash
# Tracker starten:
python3 flighttracker.py

# Tracker im Hintergrund starten:
nohup python3 flighttracker.py &
```

---

## 📤 Export / API (optional)

Wird in v1.8 erweitert:
- Export als CSV/JSON
- REST-API mit Filterung
- Live-Map mit Heading

---

## 🧼 Auto-Cleanup

Daten älter als **180 Tage** werden automatisch gelöscht.

---

## 🧪 Test

```bash
curl http://127.0.0.1:8083
```

---

## 🛠 Fehlerbehebung

Falls keine Daten kommen:

```bash
sudo journalctl -u readsb -n 50
```

Prüfe, ob Beast TCP auf Port 30005 läuft:

```bash
sudo ss -tuln | grep 30005
```

---

## Lizenz

MIT-Lizenz – frei nutzbar, auch für Vereine / Schulen.
