<p align="center">
  <img src="logo.png" alt="Flugtracker Logo" width="300"/>
</p>

# Flugtracker v1.7

Ein leichtgewichtiges ADS-B Tracking-Frontend für Flugleiter, Tower und private Plätze.

## ✈️ Funktionen

- Livekarte mit Filter für Callsign, Höhe, Radius, Zeit & Bewegungsart
- Platzrundendarstellung (GPX)
- Anflug- und Abflugerkennung (<3 NM & Höhenlogik)
- CSV-Export & OpenSky-Datenabruf
- Webansicht lokal oder über Lighttpd erreichbar (Port 80)
- Autostart & Watchdog via systemd

## 🚀 Schnellstart

```bash
cd ~
rm -rf Landetracker
git clone https://github.com/AndreasS964/Landetracker.git
cd Landetracker
bash install_flighttracker.sh
```

Dann im Browser aufrufen:

```bash
http://<IP-des-RaspberryPi>/index.html
```

## 🔄 Webzugriff

Das Frontend wird automatisch nach `/var/www/html/` kopiert und ist über Port 80 erreichbar.

## 📦 Autostart

Nach der Installation automatisch über `systemd` aktiv:

```bash
sudo systemctl status flighttracker
```

## 📁 Struktur

- `flighttracker.py` – Server & Datenlogger
- `index.html` – Web-Frontend (Filter, Karte, Tabelle, Buttons)
- `platzrunde.gpx` – GPX-Datei für Platzrunde
- `logo.png` – eingebunden im Banner und README

## 🧩 Erweiterungen geplant

- Mustererkennung (z. B. Platzrunden automatisch klassifizieren)
- Diagramme, Heatmap, Besucherhäufigkeit
- Authentifizierung, Pilotenlogbuch

---

(c) Andreas Sika · v1.7
