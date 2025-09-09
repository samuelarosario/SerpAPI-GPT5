import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "Main_DB.db"

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

# Patterns to parse existing timezone strings
# Examples handled: "+8 GMT", "-5 GMT", "+5:30 GMT", "UTC+8", "UTC-03:00", "GMT+1", "8"
p_gmt = re.compile(r"^\s*([+-]?)(\d{1,2})(?::(\d{1,2}))?\s*GMT\s*$", re.IGNORECASE)
p_utc = re.compile(r"^\s*UTC\s*([+-]?)(\d{1,2})(?::(\d{1,2}))?\s*$", re.IGNORECASE)
p_num = re.compile(r"^\s*([+-]?)(\d{1,2})(?::(\d{1,2}))?\s*$")

cur.execute("SELECT airport_code, timezone FROM airports WHERE timezone IS NOT NULL AND timezone <> ''")
rows = cur.fetchall()

updated = 0
skipped = 0

for code, tz in rows:
    tz = (tz or '').strip()
    sign = '+'
    hh = None
    mm = '00'

    m = p_gmt.match(tz) or p_utc.match(tz) or p_num.match(tz)
    if m:
        s, h, mmin = m.groups()
        if s and s in ('+', '-'):
            sign = s
        hh = int(h)
        if mmin is not None and mmin != '':
            mm = f"{int(mmin):02d}"
        else:
            mm = '00'
    else:
        skipped += 1
        continue

    if hh is None or hh > 14:  # sanity; max UTC offset is +14:00
        skipped += 1
        continue

    new_tz = f"UTC{sign}{hh:02d}:{mm}"
    if new_tz != tz:
        cur.execute("UPDATE airports SET timezone=? WHERE airport_code=?", (new_tz, code))
        if cur.rowcount:
            updated += 1

conn.commit()
conn.close()

print({'updated': updated, 'skipped': skipped, 'db': str(DB_PATH)})
