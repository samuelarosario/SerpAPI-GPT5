import os, sqlite3, tempfile, unittest, time
from datetime import datetime, timedelta
import sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN_DIR = ROOT / 'Main'
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

from cache import FlightSearchCache  # type: ignore

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS flight_searches (
  search_id TEXT PRIMARY KEY,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS flight_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  search_id TEXT
);
CREATE TABLE IF NOT EXISTS flight_segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  flight_result_id INTEGER
);
CREATE TABLE IF NOT EXISTS layovers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  flight_result_id INTEGER
);
CREATE TABLE IF NOT EXISTS price_insights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  search_id TEXT
);
CREATE TABLE IF NOT EXISTS api_queries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT
);
"""

class TestRawRetentionPolicy(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(prefix='raw_retention_', suffix='.db')
        os.close(fd)
        self.db_path = path
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA_SQL)
            old_ts = (datetime.now() - timedelta(hours=3)).isoformat()
            # Insert one old structured search + raw api row
            conn.execute("INSERT INTO flight_searches (search_id, created_at) VALUES (?, ?)", ("search_old", old_ts))
            conn.execute("INSERT INTO api_queries (created_at) VALUES (?)", (old_ts,))
            conn.commit()
        self.cache = FlightSearchCache(self.db_path)

    def tearDown(self):
        try:
            os.remove(self.db_path)
        except OSError:
            pass

    def _count(self, table):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            return cur.fetchone()[0]

    def test_raw_preserved_default_cleanup(self):
        # Ensure both present initially
        self.assertEqual(self._count('flight_searches'), 1)
        self.assertEqual(self._count('api_queries'), 1)
        # cleanup (older than 1 hour) without prune_raw should delete structured but keep raw
        self.cache.cleanup_old_data(max_age_hours=1, prune_raw=False)
        self.assertEqual(self._count('flight_searches'), 0)
        self.assertEqual(self._count('api_queries'), 1, 'Raw api_queries should be retained by default')

    def test_raw_removed_when_prune_true(self):
        # Both exist
        self.assertEqual(self._count('api_queries'), 1)
        # prune with raw
        self.cache.cleanup_old_data(max_age_hours=1, prune_raw=True)
        self.assertEqual(self._count('api_queries'), 0, 'Raw api_queries should be pruned when prune_raw=True')

if __name__ == '__main__':
    unittest.main()