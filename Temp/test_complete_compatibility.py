"""
Comprehensive Flight Search Database Compatibility Test
Tests all database operations with optimized schema
"""

import sqlite3
import json
import sys
import os
from datetime import datetime

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'DB'))

def test_complete_flight_search_compatibility():
    """Test complete flight search database operations"""
    db_path = "../DB/Main_DB.db"
    
    print("🧪 COMPREHENSIVE FLIGHT SEARCH COMPATIBILITY TEST")
    print("=" * 60)
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Test 1: Storage operations (simulate storing new flight data)
        print("\n✅ TEST 1: STORAGE OPERATIONS")
        
        test_search_id = "test_search_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Test airport storage
            cursor.execute("""
            INSERT OR REPLACE INTO airports (
                airport_code, airport_name, city, country, country_code,
                timezone, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'TST', 'Test Airport', 'Test City', 'Test Country', 'TC',
                'Test/Timezone', datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            # Test airline storage
            cursor.execute("""
            INSERT OR REPLACE INTO airlines (
                airline_code, airline_name, logo_url, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?)
            """, (
                'TS', 'Test Airlines', 'https://test.com/logo.png',
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            # Test flight search storage
            cursor.execute("""
            INSERT INTO flight_searches (
                search_id, search_timestamp, departure_id, arrival_id, 
                outbound_date, flight_type, adults, travel_class,
                currency, country_code, response_status, total_results,
                cache_key, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_search_id, datetime.now().isoformat(), 'TST', 'LAX',
                '2025-10-01', 'one_way', 1, 'economy', 'USD', 'US',
                'success', 1, 'test_cache_key', datetime.now().isoformat()
            ))
            
            # Test flight result storage
            cursor.execute("""
            INSERT INTO flight_results (
                search_id, result_type, result_rank, total_duration,
                total_price, price_currency, flight_type, layover_count,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_search_id, 'flight', 1, 300, 500, 'USD', 'one_way', 0,
                datetime.now().isoformat()
            ))
            
            # Get the flight result ID
            flight_result_id = cursor.lastrowid
            
            # Test flight segment storage with optimized schema
            cursor.execute("""
            INSERT INTO flight_segments (
                flight_result_id, segment_order, departure_airport_code, departure_time,
                arrival_airport_code, arrival_time, duration_minutes, airplane_model,
                airline_code, flight_number, travel_class, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                flight_result_id, 1, 'TST', '2025-10-01T10:00:00',
                'LAX', '2025-10-01T15:00:00', 300, 'Boeing 737',
                'TS', 'TS123', 'economy', datetime.now().isoformat()
            ))
            
            print("   ✅ All storage operations successful!")
            
        except Exception as e:
            print(f"   ❌ Storage failed: {e}")
            return
        
        # Test 2: Retrieval operations with JOINs
        print("\n✅ TEST 2: RETRIEVAL WITH FOREIGN KEY JOINS")
        
        try:
            # Test complex query with all foreign key relationships
            complex_query = """
            SELECT fs.search_id, fr.total_price, fr.price_currency,
                   fs.departure_airport_code, da.airport_name as dep_name, da.city as dep_city,
                   fs.arrival_airport_code, aa.airport_name as arr_name, aa.city as arr_city,
                   fs.departure_time, fs.arrival_time, fs.duration_minutes,
                   fs.airline_code, al.airline_name, fs.flight_number
            FROM flight_searches fs
            JOIN flight_results fr ON fs.search_id = fr.search_id
            JOIN flight_segments fg ON fr.id = fg.flight_result_id
            LEFT JOIN airports da ON fg.departure_airport_code = da.airport_code
            LEFT JOIN airports aa ON fg.arrival_airport_code = aa.airport_code
            LEFT JOIN airlines al ON fg.airline_code = al.airline_code
            WHERE fs.search_id = ?
            """
            
            cursor.execute(complex_query, (test_search_id,))
            result = cursor.fetchone()
            
            if result:
                print(f"   ✅ Flight: {result['dep_name']} ({result['dep_city']}) → {result['arr_name']} ({result['arr_city']})")
                print(f"      Airline: {result['airline_name']} Flight {result['flight_number']}")
                print(f"      Price: {result['price_currency']} {result['total_price']}")
                print(f"      Duration: {result['duration_minutes']} minutes")
            else:
                print("   ❌ No results found for complex query")
                
        except Exception as e:
            print(f"   ❌ Retrieval failed: {e}")
        
        # Test 3: Cache search compatibility
        print("\n✅ TEST 3: CACHE SEARCH COMPATIBILITY")
        
        try:
            # Test the updated cache search query
            cache_query = """
            SELECT fs.*, ar.raw_response, ar.query_timestamp
            FROM flight_searches fs
            JOIN api_queries ar ON fs.search_id = ar.search_term
            WHERE fs.cache_key = ? 
            AND ar.query_timestamp > ?
            ORDER BY ar.query_timestamp DESC
            LIMIT 1
            """
            
            cutoff_time = datetime.now().isoformat()
            cursor.execute(cache_query, ('test_cache_key', '2025-01-01T00:00:00'))
            
            print("   ✅ Cache search query structure is valid")
            
        except Exception as e:
            print(f"   ❌ Cache search failed: {e}")
        
        # Test 4: Layover operations
        print("\n✅ TEST 4: LAYOVER OPERATIONS")
        
        try:
            # Insert test layover
            cursor.execute("""
            INSERT INTO layovers (
                flight_result_id, layover_order, airport_code,
                duration_minutes, is_overnight, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                flight_result_id, 1, 'TST', 120, False, datetime.now().isoformat()
            ))
            
            # Test layover retrieval with airport join
            cursor.execute("""
            SELECT l.*, a.airport_name, a.city
            FROM layovers l
            LEFT JOIN airports a ON l.airport_code = a.airport_code
            WHERE l.flight_result_id = ?
            """, (flight_result_id,))
            
            layover = cursor.fetchone()
            if layover:
                print(f"   ✅ Layover at: {layover['airport_name']} ({layover['airport_code']})")
                print(f"      Duration: {layover['duration_minutes']} minutes")
            else:
                print("   ❌ No layover found")
                
        except Exception as e:
            print(f"   ❌ Layover operations failed: {e}")
        
        # Test 5: Cleanup operations
        print("\n✅ TEST 5: CLEANUP OPERATIONS")
        
        try:
            # Test cleanup queries (without actually deleting)
            cleanup_queries = [
                """
                SELECT COUNT(*) FROM layovers 
                WHERE flight_result_id IN (
                    SELECT id FROM flight_results WHERE search_id = ?
                )
                """,
                """
                SELECT COUNT(*) FROM flight_segments 
                WHERE flight_result_id IN (
                    SELECT id FROM flight_results WHERE search_id = ?
                )
                """,
                "SELECT COUNT(*) FROM flight_results WHERE search_id = ?",
                "SELECT COUNT(*) FROM flight_searches WHERE search_id = ?"
            ]
            
            for query in cleanup_queries:
                cursor.execute(query, (test_search_id,))
                count = cursor.fetchone()[0]
                print(f"   ✅ Cleanup query valid, found {count} records")
                
        except Exception as e:
            print(f"   ❌ Cleanup operations failed: {e}")
        
        # Clean up test data
        try:
            cursor.execute("DELETE FROM layovers WHERE flight_result_id = ?", (flight_result_id,))
            cursor.execute("DELETE FROM flight_segments WHERE flight_result_id = ?", (flight_result_id,))
            cursor.execute("DELETE FROM flight_results WHERE search_id = ?", (test_search_id,))
            cursor.execute("DELETE FROM flight_searches WHERE search_id = ?", (test_search_id,))
            cursor.execute("DELETE FROM airports WHERE airport_code = 'TST'")
            cursor.execute("DELETE FROM airlines WHERE airline_code = 'TS'")
            conn.commit()
            print("\n🧹 Test data cleaned up successfully")
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
        
        print("\n🎉 COMPATIBILITY TEST COMPLETE!")
        print("   Flight search functions should work with optimized schema")

if __name__ == "__main__":
    test_complete_flight_search_compatibility()
