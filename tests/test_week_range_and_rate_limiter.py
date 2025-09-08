import os, sys, sqlite3, tempfile, types, json
from datetime import datetime, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN_DIR = os.path.join(ROOT, 'Main')
if MAIN_DIR not in sys.path:
    sys.path.insert(0, MAIN_DIR)

from enhanced_flight_search import EnhancedFlightSearchClient  # type: ignore
from core.common_validation import RateLimiter  # type: ignore


class DummyAPI:
    """Deterministic mock of SerpAPIFlightClient returning synthetic flights."""
    def __init__(self):
        self.calls = []
    def search_round_trip(self, **kwargs):  # signature alignment
        self.calls.append(kwargs)
        # Minimal predictable payload
        d = kwargs.get('outbound_date')
        price_base = int(d.split('-')[-1])  # vary by day numeric for diversity
        flight_template = {
            'price': f"{price_base * 10} USD",
            'total_duration': 120 + price_base,
            'layovers': [],
            'flights': [
                {
                    'departure_airport': {'id': kwargs['departure_id']},
                    'arrival_airport': {'id': kwargs['arrival_id']},
                    'duration': 120,
                    'airline': 'XX',
                    'flight_number': 'XX100',
                }
            ]
        }
        return {
            'success': True,
            'search_id': f"mock_{len(self.calls)}",
            'data': {
                'best_flights': [flight_template],
                'other_flights': [],
                'price_insights': {'lowest_price': price_base * 10, 'price_level': 'low', 'typical_price_range': [price_base * 8, price_base * 12], 'price_history': []}
            }
        }
    # one-way path unused in week range test
    def search_one_way(self, **kwargs):  # pragma: no cover
        return self.search_round_trip(**kwargs)


def _init_memory_db(client: EnhancedFlightSearchClient):
    # Point client to a temporary db with minimal required tables
    schema = """
    CREATE TABLE flight_searches (
        search_id TEXT PRIMARY KEY,
        search_timestamp TEXT,
        departure_airport_code TEXT,
        arrival_airport_code TEXT,
        outbound_date TEXT,
        return_date TEXT,
        flight_type INTEGER,
        adults INTEGER,
        children INTEGER,
        infants_in_seat INTEGER,
        infants_on_lap INTEGER,
        travel_class INTEGER,
        currency TEXT,
        country_code TEXT,
        language_code TEXT,
        raw_parameters TEXT,
        response_status TEXT,
        total_results INTEGER,
        cache_key TEXT,
        api_query_id INTEGER,
        created_at TEXT
    );
    CREATE TABLE flight_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        search_id TEXT,
        result_type TEXT,
        result_rank INTEGER,
        total_duration INTEGER,
        total_price INTEGER,
        price_currency TEXT,
        flight_type TEXT,
        layover_count INTEGER,
        carbon_emissions_flight INTEGER,
        carbon_emissions_typical INTEGER,
        carbon_emissions_difference_percent INTEGER,
        departure_token TEXT,
        booking_token TEXT,
        airline_logo_url TEXT,
        created_at TEXT
    );
    CREATE TABLE flight_segments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_result_id INTEGER,
        segment_order INTEGER,
        departure_airport_code TEXT,
        departure_time TEXT,
        arrival_airport_code TEXT,
        arrival_time TEXT,
        duration_minutes INTEGER,
        airplane_model TEXT,
        airline_code TEXT,
        flight_number TEXT,
        travel_class TEXT,
        legroom TEXT,
        often_delayed BOOLEAN,
        extensions TEXT,
        created_at TEXT
    );
    CREATE TABLE layovers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_result_id INTEGER,
        layover_order INTEGER,
        airport_code TEXT,
        duration_minutes INTEGER,
        is_overnight BOOLEAN,
        created_at TEXT
    );
    CREATE TABLE price_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        search_id TEXT,
        lowest_price INTEGER,
        price_level TEXT,
        typical_price_low INTEGER,
        typical_price_high INTEGER,
        price_history TEXT,
        created_at TEXT
    );
    CREATE TABLE api_queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query_parameters TEXT,
        raw_response TEXT,
        query_type TEXT,
        status_code INTEGER,
        response_size INTEGER,
        api_endpoint TEXT,
        search_term TEXT,
        created_at TEXT
    );
    """
    fd, path = tempfile.mkstemp(prefix='efs_week_', suffix='.db')
    os.close(fd)
    client.db_path = path
    with sqlite3.connect(client.db_path) as conn:
        conn.executescript(schema)
    return path


def test_week_range_aggregation():
    client = EnhancedFlightSearchClient(api_key='dummy')
    _init_memory_db(client)
    # Inject dummy api client
    client.api_client = DummyAPI()
    start = datetime.now().date() + timedelta(days=5)
    res = client.search_week_range('LAX', 'JFK', start.strftime('%Y-%m-%d'))
    assert res['success']
    summary = res['summary']
    assert summary['total_days_searched'] == 7
    # Ensure aggregation captured flights
    assert summary['total_flights_found'] == 7  # one per day from dummy
    assert len(res['best_week_flights']) == 7
    # Trend object present
    assert 'price_trend' in res


def test_rate_limiter_boundary():
    rl = RateLimiter()
    # Simulate exhausting minute quota
    for _ in range(rl._minute.__len__()):  # ensure empty
        pass
    # Fill minute window to limit
    if MAIN_DIR not in sys.path:
        sys.path.insert(0, MAIN_DIR)
    from config import RATE_LIMIT_CONFIG  # type: ignore
    for _ in range(RATE_LIMIT_CONFIG['requests_per_minute']):
        rl.record_request()
    assert not rl.can_make_request(), 'Rate limiter should block immediately after hitting minute quota'
    # Advance time by >60s by manipulating internal timestamps
    past = datetime.now() - timedelta(seconds=61)
    rl._minute = [past for _ in rl._minute]
    assert rl.can_make_request(), 'Rate limiter should allow after window expiration'
