import http.server
import socketserver
import sqlite3
import requests
import time
import math
from datetime import datetime
import csv
from urllib.parse import urlparse, parse_qs
import html
import threading
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from string import Template

# Configuration
PORT = 8083
DB_PATH = 'flugdaten.db'
AIRCRAFT_CSV = 'aircraft_db.csv'
MISSING_LOG = 'missing_muster.log'
EDTW_LAT = 48.27889122038788
EDTW_LON = 8.42936618151063
MAX_RADIUS_NM = 5
VERSION = '1.6'
FETCH_INTERVAL = 300  # seconds
WATCHDOG_INTERVAL = 10  # seconds
DB_UPDATE_INTERVAL = 30 * 24 * 3600  # 30 days

# HTML Template mit Bootstrap, Farben, Karte & Links zu tar1090/graphs1090
MAIN_TEMPLATE = Template(r"""
<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>Flugtracker EDTW</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>body{padding:20px;} table.dataTable tbody tr:hover{background:#f0f0f0;} .low{color:green;} .mid{color:orange;} .high{color:red;}</style>
</head><body>
<div class="container">
<h3 class="mb-3">Flugtracker EDTW – Version $version</h3>
<div class="mb-3">
  <a href="/log" class="btn btn-secondary btn-sm">Log</a>
  <a href="/stats" class="btn btn-secondary btn-sm">Statistik</a>
  <a href="/reset" class="btn btn-danger btn-sm" onclick="return confirm('DB wirklich löschen?');">Datenbank zurücksetzen</a>
  <a href="/tar1090" class="btn btn-outline-primary btn-sm" target="_blank">tar1090</a>
  <a href="/graphs1090" class="btn btn-outline-primary btn-sm" target="_blank">graphs1090</a>
</div>
<form method="GET" action="/" class="row g-3">
  <div class="col-auto">
    <label class="form-label">Radius (nm)</label>
    <input type="number" name="radius" value="$radius" class="form-control">
  </div>
  <div class="col-auto">
    <label class="form-label">Höhenfilter</label>
    <select name="altfilter" class="form-select">
      <option value="all" $altall>Alle</option>
      <option value="3000" $alt3000><3000ft</option>
      <option value="5000" $alt5000><5000ft</option>
    </select>
  </div>
  <div class="col-auto">
    <label class="form-label">Datum</label>
    <input type="date" name="date" value="$date" class="form-control">
  </div>
  <div class="col-auto align-self-end">
    <button type="submit" class="btn btn-primary">Anzeigen</button>
  </div>
</form>
<div id="map" style="height:300px;margin-top:20px;"></div>
<table id="flugtable" class="table table-striped"><thead><tr>
<th>Call</th><th>Höhe</th><th>Geschw.</th><th>Muster</th><th>Zeit</th><th>Datum</th></tr></thead><tbody>$rows</tbody></table>
<p class="text-muted small">© Andreas Sika – Version $version</p>
</div>
<script>
$(document).ready(function() { $('#flugtable').DataTable(); });
var map = L.map('map').setView([$lat, $lon], 11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap-Mitwirkende'
}).addTo(map);
L.circle([$lat, $lon], {radius: $radius_m, color: 'blue'}).addTo(map);

// Optional: dynamischer Marker Layer für spätere Erweiterung vorbereiten
var aircraftLayer = L.layerGroup().addTo(map);
// Beispiel: aircraftLayer.clearLayers(); aircraftLayer.addLayer(...)
</script>
</body></html>
""")
