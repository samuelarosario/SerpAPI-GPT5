-- Migration: Drop unused columns from airports table
-- Columns to drop: first_seen, last_seen, thumbnail_url, image_url
-- SQLite requires table rebuild for DROP COLUMN in older versions

PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

-- 1) Create new table without the columns
CREATE TABLE airports_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    airport_code TEXT UNIQUE NOT NULL,
    airport_name TEXT NOT NULL,
    city TEXT,
    country TEXT,
    country_code TEXT,
    timezone TEXT
);

-- 2) Copy data
INSERT INTO airports_new (id, airport_code, airport_name, city, country, country_code, timezone)
SELECT id, airport_code, airport_name, city, country, country_code, timezone
FROM airports;

-- 3) Drop old table and rename
DROP TABLE airports;
ALTER TABLE airports_new RENAME TO airports;

-- 4) Recreate indexes if any
CREATE INDEX IF NOT EXISTS idx_airports_code ON airports(airport_code);

COMMIT;
PRAGMA foreign_keys=ON;
