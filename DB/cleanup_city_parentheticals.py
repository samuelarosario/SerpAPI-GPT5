import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "Main_DB.db"

pat = re.compile(r"\s*\([^)]*\)")

conn = sqlite3.connect(str(DB_PATH))
conn.execute("PRAGMA foreign_keys=ON")
cur = conn.cursor()

cur.execute("SELECT airport_code, city FROM airports WHERE city IS NOT NULL AND (city LIKE '%(%' OR city LIKE '%)%')")
rows = cur.fetchall()

changed = 0
for code, city in rows:
    new_city = pat.sub("", city).strip()
    # collapse double spaces
    new_city = re.sub(r"\s{2,}", " ", new_city)
    if new_city != city:
        cur.execute("UPDATE airports SET city=? WHERE airport_code=?", (new_city if new_city else None, code))
        changed += 1

conn.commit()
conn.close()

print({
    'db': str(DB_PATH),
    'scanned': len(rows),
    'updated': changed,
})
