import json
import sqlite3
from datetime import datetime
from Main.persistence.structured_writer import StructuredFlightWriter

# Minimal in-memory schema subset to validate inserts
SCHEMA = [
"""CREATE TABLE airports(airport_code TEXT PRIMARY KEY, airport_name TEXT);""",
"""CREATE TABLE airlines(airline_code TEXT PRIMARY KEY, airline_name TEXT);""",
"""CREATE TABLE flight_searches( search_id TEXT PRIMARY KEY, search_timestamp TEXT, departure_airport_code TEXT, arrival_airport_code TEXT, outbound_date TEXT, return_date TEXT, flight_type INTEGER, adults INTEGER, children INTEGER, infants_in_seat INTEGER, infants_on_lap INTEGER, travel_class INTEGER, currency TEXT, country_code TEXT, language_code TEXT, raw_parameters TEXT, response_status TEXT, total_results INTEGER, cache_key TEXT, api_query_id INTEGER, created_at TEXT);""",
"""CREATE TABLE flight_results( id INTEGER PRIMARY KEY AUTOINCREMENT, search_id TEXT, result_type TEXT, result_rank INTEGER, total_duration INTEGER, total_price TEXT, price_currency TEXT, flight_type TEXT, layover_count INTEGER, carbon_emissions_flight INTEGER, carbon_emissions_typical INTEGER, carbon_emissions_difference_percent INTEGER, departure_token TEXT, booking_token TEXT, airline_logo_url TEXT, created_at TEXT);""",
"""CREATE TABLE flight_segments( id INTEGER PRIMARY KEY AUTOINCREMENT, flight_result_id INTEGER, segment_order INTEGER, departure_airport_code TEXT, departure_time TEXT, arrival_airport_code TEXT, arrival_time TEXT, duration_minutes INTEGER, airplane_model TEXT, airline_code TEXT, flight_number TEXT, travel_class TEXT, legroom TEXT, often_delayed INTEGER, extensions TEXT, created_at TEXT);""",
"""CREATE TABLE layovers( id INTEGER PRIMARY KEY AUTOINCREMENT, flight_result_id INTEGER, layover_order INTEGER, airport_code TEXT, duration_minutes INTEGER, is_overnight INTEGER, created_at TEXT);""",
"""CREATE TABLE price_insights( search_id TEXT PRIMARY KEY, lowest_price INTEGER, price_level TEXT, typical_price_low INTEGER, typical_price_high INTEGER, price_history TEXT, created_at TEXT);"""
]

def build_conn():
    conn = sqlite3.connect(":memory:")
    for s in SCHEMA:
        conn.execute(s)
    return conn

class DummyCacheKeyGen:
    def generate_cache_key(self, params):
        return 'cache:'+params.get('departure_id','')+params.get('arrival_id','')

def test_structured_writer_basic(monkeypatch):
    # Patch FlightSearchCache inside writer to avoid hitting real DB
    from Main import cache as cache_mod
    monkeypatch.setattr(cache_mod, 'FlightSearchCache', lambda db_path: DummyCacheKeyGen())
    conn = build_conn()
    monkeypatch.setattr('Main.persistence.structured_writer.open_connection', lambda _path: conn)
    writer = StructuredFlightWriter('ignored.db')
    params = {'departure_id':'AAA','arrival_id':'BBB','outbound_date':'2025-12-01','return_date':'2025-12-08','adults':1,'children':0,'travel_class':1,'currency':'USD'}
    api = {'best_flights':[{'price':'123 USD','flights':[{'departure_airport':{'id':'AAA','time':'2025-12-01T10:00'},'arrival_airport':{'id':'BBB','time':'2025-12-01T12:00'},'duration':120,'airline':'AB','flight_number':'AB 100'}]}], 'other_flights':[], 'price_insights':{'lowest_price':123,'price_level':'average','typical_price_range':[100,150],'price_history':[120,130,125]}}
    writer.store('S1', params, api, api_query_id=1)
    # Assertions
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM flight_searches'); assert cur.fetchone()[0] == 1
    cur.execute('SELECT COUNT(*) FROM flight_results'); assert cur.fetchone()[0] == 1
    cur.execute('SELECT COUNT(*) FROM flight_segments'); assert cur.fetchone()[0] == 1
    cur.execute('SELECT COUNT(*) FROM price_insights'); assert cur.fetchone()[0] == 1
    # Idempotency (second call should not duplicate)
    writer.store('S1', params, api, api_query_id=1)
    cur.execute('SELECT COUNT(*) FROM flight_results'); assert cur.fetchone()[0] == 1
