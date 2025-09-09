import csv
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "DB" / "Main_DB.db"
CSV_PATH = ROOT / "DB" / "airports.csv"

assert DB_PATH.exists(), f"DB not found: {DB_PATH}"
assert CSV_PATH.exists(), f"CSV not found: {CSV_PATH}"

conn = sqlite3.connect(str(DB_PATH))
conn.execute("PRAGMA foreign_keys=ON")
cur = conn.cursor()

inserted = 0
updated = 0
skipped = 0

with open(CSV_PATH, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    # Expected headers: name, iso_country, municipality, icao_code, iata_code
    rows = list(reader)

conn.execute("BEGIN")
try:
    for r in rows:
        iata = (r.get('iata_code') or '').strip()
        name = (r.get('name') or '').strip()
        country_code = (r.get('iso_country') or '').strip()
        city = (r.get('municipality') or '').strip()

        if not iata:
            skipped += 1
            continue

        # Use uppercase to standardize codes while writing
        code = iata.upper()

        # Upsert: overwrite airport_name, country_code, city for existing codes
        cur.execute(
            """
            INSERT INTO airports (airport_code, airport_name, country_code, city)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(airport_code) DO UPDATE SET
                airport_name=excluded.airport_name,
                country_code=excluded.country_code,
                city=excluded.city
            """,
            (code, name or code, country_code or None, city or None)
        )
        if cur.rowcount == 1 and cur.lastrowid is not None:
            inserted += 1
        else:
            # SQLite rowcount on upsert can be tricky; count as updated if code existed
            updated += 1

    conn.commit()
finally:
    conn.close()

print({
    'inserted': inserted,
    'updated': updated,
    'skipped_no_iata': skipped,
    'db': str(DB_PATH),
    'csv': str(CSV_PATH),
})
