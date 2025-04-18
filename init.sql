CREATE TABLE IF NOT EXISTS flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    icao TEXT,
    callsign TEXT,
    lat REAL,
    lon REAL,
    alt INTEGER,
    track INTEGER,
    speed INTEGER,
    time TEXT
);