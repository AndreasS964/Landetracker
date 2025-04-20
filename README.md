# ✈️ Flugtracker v1.8

Ein leichtgewichtiges, autarkes Tracking-System für Flugbewegungen rund um EDTW. Funktioniert ganz ohne Cloud, lokal auf einem Raspberry Pi mit SDR-Stick.

## 🧰 Features

- ADS-B Empfang über `readsb` (lokal)
- Alternativ/Ausfallsicher: Online-Abruf via [`adsb.lol`](https://api.adsb.lol)
- Speicherung der Flüge in SQLite
- Darstellung auf Webkarte (Leaflet)
- Filter für:
  - Datum von–bis
  - Bewegungsart (Anflug, Abflug, Platzrunde)
  - Höhe / Radius / Geschwindigkeit
- CSV/JSON Export & Statistikansicht
- Platzrunde (.gpx)
- Autostart & Watchdog über systemd
- ✅ Kein Flask! Reiner HTTP-Server (Standardlib)

## 🚀 Installation (Pi, clean)

```bash
bash install_flighttracker.sh
```

## 🔧 Manuell starten

```bash
python3 ~/Landetracker/flighttracker.py
```

## 🔁 Bewegungsarten

- **Anflug**: unter 3200 ft und < 3 NM
- **Abflug**: über 3200 ft und < 3 NM
- **Platzrunde**: <= 5 NM mit niedriger Höhe & kurzem Abstand

## 📦 Systemdienste

- `flighttracker.service` (Autostart & Watchdog)
- `readsb.service` (ADS-B Empfänger)
- DuckDNS (`duck.sh` via Cron alle 5 Minuten)

## 📂 Verzeichnisstruktur

| Datei                | Funktion                            |
|----------------------|-------------------------------------|
| `flighttracker.py`   | Hauptserver                         |
| `index.html`         | Web-Frontend (Filter, Karte etc.)   |
| `flugdaten.db`       | SQLite-Datenbank                    |
| `tracker.log`        | Laufendes Logfile                   |
| `platzrunde.gpx`     | Platzrunde-Datei (optional)         |
| `logo.png`           | eigenes Logo (optional)             |

## 📈 Statistikseite

Erreichbar über:
```
http://<raspi-ip>:8083/stats
```

## 📋 Loganzeige

Erreichbar über:
```
http://<raspi-ip>:8083/log
```

## 🌐 Links

- [adsb.lol API](https://api.adsb.lol/docs)
- [readsb](https://github.com/wiedehopf/readsb)
- [Leaflet JS](https://leafletjs.com/)
- [DuckDNS](https://www.duckdns.org/)
