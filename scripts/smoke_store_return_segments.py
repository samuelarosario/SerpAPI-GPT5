import json
import os
import random
import sqlite3
import sys
from datetime import datetime

# Adjust sys.path similar to WebApp so that 'Main' and 'core' resolve
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN_DIR = os.path.join(ROOT, 'Main')
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if MAIN_DIR not in sys.path:
    sys.path.insert(0, MAIN_DIR)

from Main.enhanced_flight_search import EnhancedFlightSearchClient

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'DB', 'Main_DB.db')
DB_PATH = os.path.normpath(DB_PATH)

# Build a minimal round-trip-like payload with unknown return airports
api_response = {
    "best_flights": [
        {
            "price": 123,
            "type": "Round trip",
            "total_duration": 180,
            "flights": [
                {  # outbound segment (ensure known)
                    "departure_airport": {"id": "MNL", "time": "2025-11-30T08:00:00"},
                    "arrival_airport": {"id": "POM", "time": "2025-11-30T11:00:00"},
                    "duration": 180,
                    "airplane": "A320",
                    "airline": "PX",
                    "flight_number": "PX 123"
                },
                {  # return segment with unknown airports (should be upserted)
                    "departure_airport": {"id": "ZZ1", "time": "2025-12-07T14:00:00"},
                    "arrival_airport": {"id": "ZZ2", "time": "2025-12-07T18:00:00"},
                    "duration": 240,
                    "airplane": "A321",
                    "airline": "PX",
                    "flight_number": "PX 456"
                }
            ],
            "layovers": [
                {"id": "ZZ3", "duration": 45, "overnight": False}
            ],
            "carbon_emissions": {"this_flight": 100}
        }
    ],
    "other_flights": []
}

# Prepare client (pass dummy API key to avoid env lookup)
client = EnhancedFlightSearchClient(api_key="dummy", db_path=DB_PATH)

# Randomized search id
search_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}"

search_params = {
    "departure_id": "MNL",
    "arrival_id": "POM",
    "outbound_date": "2025-11-30",
    "return_date": "2025-12-07",
    "adults": 1,
    "travel_class": 1,
    "currency": "USD"
}

# Invoke structured storage
client._store_structured_data(search_id, search_params, api_response, api_query_id=None)

# Inspect counts
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM flight_results WHERE search_id=?", (search_id,))
fr = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM flight_segments fs JOIN flight_results fr ON fs.flight_result_id=fr.id WHERE fr.search_id=?", (search_id,))
seg = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM layovers l JOIN flight_results fr ON l.flight_result_id=fr.id WHERE fr.search_id=?", (search_id,))
lay = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM airports WHERE airport_code IN ('ZZ1','ZZ2','ZZ3')")
auto_air = cur.fetchone()[0]
conn.close()

print(json.dumps({
    "search_id": search_id,
    "flight_results": fr,
    "segments": seg,
    "layovers": lay,
    "auto_airports_inserted": auto_air
}, indent=2))
