from datetime import datetime
import sqlite3
from pathlib import Path

import pytz  # type: ignore

DB_PATH = Path(__file__).resolve().parent / "Main_DB.db"

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

cur.execute("SELECT airport_code, timezone FROM airports WHERE timezone IS NOT NULL AND timezone <> ''")
rows = cur.fetchall()

updated = 0
skipped = 0

for code, tzname in rows:
    tzname = (tzname or '').strip()
    # If already looks like an offset string, skip
    if tzname.upper().startswith(('GMT', 'UTC')) or any(ch.isdigit() for ch in tzname) and ('/' not in tzname):
        skipped += 1
        continue
    try:
        tz = pytz.timezone(tzname)
        # Current offset from UTC at runtime
        now = datetime.now(pytz.utc).astimezone(tz)
        offset = now.utcoffset()
        if offset is None:
            skipped += 1
            continue
        total_minutes = int(offset.total_seconds() // 60)
        sign = '+' if total_minutes >= 0 else '-'
        m = abs(total_minutes)
        hours = m // 60
        minutes = m % 60
        if minutes:
            offset_str = f"{sign}{hours}:{minutes:02d} GMT"
        else:
            offset_str = f"{sign}{hours} GMT"
        cur.execute("UPDATE airports SET timezone=? WHERE airport_code=?", (offset_str, code))
        if cur.rowcount:
            updated += 1
    except Exception:
        skipped += 1

conn.commit()
conn.close()

print({
    'updated': updated,
    'skipped': skipped,
    'db': str(DB_PATH),
})
