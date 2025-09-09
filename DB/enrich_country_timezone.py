import sqlite3
import unicodedata
from pathlib import Path

try:
    import pycountry  # type: ignore
except Exception:
    pycountry = None

try:
    import pytz  # type: ignore
except Exception:
    pytz = None

DB_PATH = Path(__file__).resolve().parent / "Main_DB.db"

if not DB_PATH.exists():
    raise SystemExit(f"DB not found: {DB_PATH}")

# Helpers

def normalize_city(s: str) -> str:
    s = s.strip()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace('-', ' ').replace('_', ' ')
    s = ' '.join(s.split())
    return s

conn = sqlite3.connect(str(DB_PATH))
conn.execute("PRAGMA foreign_keys=ON")
cur = conn.cursor()

cur.execute("SELECT airport_code, country_code, city FROM airports WHERE country_code IS NOT NULL AND country_code <> ''")
rows = cur.fetchall()

updated = 0
missing_country = 0
missing_tz_lib = pytz is None
missing_country_lib = pycountry is None

# Pre-build country name cache
country_name_cache = {}
if pycountry is not None:
    for c in list(pycountry.countries):
        country_name_cache[c.alpha_2.upper()] = c.name

for code, cc, city in rows:
    cc2 = (cc or '').upper().strip()
    # Resolve country name
    country_name = None
    if cc2 and country_name_cache:
        country_name = country_name_cache.get(cc2)

    # Resolve timezone (best-effort)
    tz_val = None
    if pytz is not None and cc2:
        tzs = pytz.country_timezones.get(cc2)
        if tzs:
            if len(tzs) == 1:
                tz_val = tzs[0]
            else:
                if city:
                    ncity = normalize_city(city)
                    # try to match the city part of tz name
                    best = None
                    for tz in tzs:
                        city_part = tz.split('/')[-1]
                        city_norm = normalize_city(city_part.replace('/', ' '))
                        if ncity and ncity in city_norm:
                            best = tz
                            break
                    tz_val = best or tzs[0]
                else:
                    tz_val = tzs[0]

    # Apply updates when we have at least one value to change
    set_parts = []
    params = []
    if country_name:
        set_parts.append("country = ?")
        params.append(country_name)
    if tz_val:
        set_parts.append("timezone = ?")
        params.append(tz_val)

    if set_parts:
        params.append(code)
        cur.execute(f"UPDATE airports SET {', '.join(set_parts)} WHERE airport_code = ?", params)
        if cur.rowcount:
            updated += 1

conn.commit()
conn.close()

print({
    'db': str(DB_PATH),
    'records_scanned': len(rows),
    'updated_rows': updated,
    'used_pycountry': not missing_country_lib,
    'used_pytz': not missing_tz_lib,
})
