# ✈️ Flugtracker v2.0 – Der lokale ADS-B Radar für Flugleiter & Spotter

<p align="center">
  <img src="logo.png" alt="Flugtracker Logo" width="250" />
</p>

---

## 🧭 Was ist der Flugtracker?

Ein autark laufendes Tracking-System für Flugbewegungen rund um Flugplätze. Läuft lokal auf einem Raspberry Pi mit SDR-Stick – ohne Cloud oder externe Server.

---

## 🔧 Funktionen

- 📡 **ADS-B Empfang** lokal über `readsb`, alternativ Online-Abruf über `adsb.lol`
- 📈 **Datenbank (SQLite)** mit allen Flügen inkl. Position, Zeit, Höhe, Geschwindigkeit, Flugzeugtyp
- 🔍 **Filterbare Weboberfläche**: Zeit, Radius, Höhe, Anflug/Abflug/Platzrunde
- 🛬 **Platzrunde-Darstellung** mit exakter `platzrunde.gpx`-Datei
- 📊 **Statistiken**: Landungen pro Tag, meistgenutzte Flugzeugtypen, Stoßzeiten
- 📁 **Exportfunktion**: CSV-Datei auf Knopfdruck
- 🔗 **Links zu tar1090 und graphs1090** integriert
- 🏠 **Lokaler Webserver** auf Port `8083`, mit automatischer Weiterleitung auf Port 80
- ✨ **Schlankes HTML/JS-Frontend** ohne Flask oder andere Serverframeworks

<p align="center">
  <img src="Screenshot 2025-05-01 211928.png" alt="Flugtracker Webansicht" width="90%" />
</p>

---

## 🚀 Neu in Version 2.0 (geplant / in Arbeit)

- ▶️ **Bewegte Flugzeugsymbole mit Heading-Darstellung** auf der Karte
- 🌐 **Unterschiedliche Icons je nach Flugzeugtyp / Höhe / Geschwindigkeit**
- ⏳ **Live-Refresh ohne Seitenreload**
- 🔄 **Optimiertes, responsives Webdesign**
- 🏡 **DynDNS-Support**: Zugriff von außen über DuckDNS / DynDNS.org
- ⚖️ **Performantere SQLite-Abfragen mit Indexen**

---

## ⚙️ Installation

```bash
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker
bash install_flighttracker.sh
```

Anschließend erreichbar unter:

```
http://<raspi-ip>:8083
```

Oder direkt via Weiterleitung:

```
http://<raspi-ip>
```

---

## 🛠️ Start & Betrieb

Manueller Start:

```bash
python3 /opt/flugtracker/flighttracker.py
```

Systemdienst aktivieren (optional):

```bash
sudo systemctl enable --now flugtracker.service
```

---

## 🔍 Beispiel-Funktionen

- **CSV-Export**: `/export.csv`
- **Statistik-API**: `/stats`
- **Loganzeige**: `/log`
- **Live-Daten**: `/flights.json`
- **adsb.lol-Abruf**: Button oder `/api/adsb`

---

## 📝 Platzrunde

Als GPX-Datei unter `/opt/flugtracker/platzrunde.gpx` einbindbar. Wird automatisch auf der Karte dargestellt.

---

## 🛡️ DynDNS Zugriff (Optional)

Falls gewünscht, kann ein DynDNS-Dienst (z. B. DuckDNS) eingerichtet werden.

Beispiel per Cronjob (`duck.sh`):

```bash
*/5 * * * * /opt/flugtracker/duck.sh >/dev/null 2>&1
```

---

## 💻 Systemaufbau

<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Raspberry_Pi_4_Model_B_-_Side.jpg/800px-Raspberry_Pi_4_Model_B_-_Side.jpg" alt="Beispiel Raspberry Pi Setup" width="450" />
</p>

- Raspberry Pi 4B mit Kühlkörpern
- SDR-USB-Stick mit Antenne
- Optional: aktiver USB-Hub, Gehäuse, LTE-Stick

---

## 🗺️ Systemübersicht (Datenfluss)

<p align="center">
  <img src="A_README_image_for_"Flugtracker",_an_aircraft_trac.png" alt="Datenfluss Flugtracker" width="700" />
</p>

**Ablauf:**
1. ✈️ Flugdaten per ADS-B empfangen (SDR + readsb)
2. 📤 Alternativabruf über adsb.lol API
3. 💾 Speicherung in SQLite-Datenbank (`flugdaten.db`)
4. 🖥️ Anzeige im Web-Frontend (`index.html`) mit Karte & Tabelle
5. 📊 Statistische Auswertungen + Export / API-Endpunkte

---

## 📁 Verzeichnisstruktur

| Datei                      | Zweck                              |
| -------------------------- | ---------------------------------- |
| `flighttracker.py`         | Hauptserver mit Web-Frontend & API |
| `index.html`               | Benutzeroberfläche (ohne Flask!)   |
| `platzrunde.gpx`           | Pfad der Platzrunde                |
| `aircraft_db.csv`          | Liste mit bekannten Flugzeugtypen  |
| `flugdaten.db`             | SQLite-Datenbank aller Flüge       |
| `tracker.log`              | Laufendes Logfile                  |
| `install_flighttracker.sh` | Automatischer Installer            |

---


