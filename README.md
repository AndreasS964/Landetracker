# 🛩️ Flugtracker v1.8

Ein lokaler Flugtracker für Flugleiter und Spotter:  
Erfasst Flugbewegungen über ADS-B (readsb oder adsb.lol), speichert sie lokal in SQLite und zeigt sie übersichtlich im Browser.

---

## 🚀 Features

- Lokale Datenbank aller empfangenen Flüge (`flugdaten.db`)
- Anzeige auf interaktiver Karte (Leaflet)
- Platzrunde als GPX-Overlay
- Filter nach Anflug, Abflug, Radius, Zeitraum
- Statistikdiagramm (Chart.js)
- CSV/JSON-Export
- Autostart via systemd
- Logo + UI im Flugleiter-Stil
- OpenSky entfernt → ersetzt durch **adsb.lol API**

---

## 🔧 Installation

```bash
bash install_flighttracker.sh
```

Das Skript installiert:
- Systempakete (`git`, `sqlite3`, `rtl-sdr`, `python3`)
- ADS-B Empfänger (`readsb`)
- Projektcode aus GitHub
- Platzrunde & Logo (falls vorhanden)
- Systemd-Autostart

---

## 🧪 Start (manuell)

```bash
cd ~/Landetracker
source venv-tracker/bin/activate
python3 flighttracker.py
```

Weboberfläche unter:  
👉 http://<IP-Adresse>:8083/

---

## 🌐 Datenquellen

### Lokal (Standard)
- `readsb` mit JSON-Ausgabe unter `/run/readsb/aircraft.json`

### Online (Fallback/Ergänzung)
- `https://api.adsb.lol/v2/aircraft?lat=...&lon=...&radius=...`

---

## ✈️ Bewegungsarten

- **Anflug**: unter 3200 ft, innerhalb 3 NM
- **Abflug**: über 3200 ft, innerhalb 3 NM
- **Platzrunde**: innerhalb definierter GPX-Strecke

---

## 📂 Dateien

| Datei             | Beschreibung                    |
|------------------|----------------------------------|
| `flighttracker.py` | Haupt-Backend                   |
| `index.html`       | UI im Flugleiter-Stil           |
| `platzrunde.gpx`   | Platzrunde (optional)           |
| `logo.png`         | Logo oben in der UI             |
| `tracker.log`      | Logfile                         |
| `install_flighttracker.sh` | Installer               |

---

## 📡 Tar1090-Kompatibilität

readsb schreibt nach `/run/readsb`, kompatibel mit tar1090.  
Tar1090 läuft separat unter:  
👉 http://<IP-Adresse>/tar1090

---

## 🔐 Entwickler

© 2025 Andreas Sika – Flugtracker powered by Enthusiasmus, Kaffee und `adsb.lol`