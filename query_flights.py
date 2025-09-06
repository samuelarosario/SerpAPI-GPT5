#!/usr/bin/env python3
"""
Query all flights from the SerpAPI database
"""

import sys
import os
sys.path.append('DB')
from database_helper import SerpAPIDatabase
import sqlite3

def query_all_flights():
    """Query and display all flight data from the database"""
    
    # Initialize database connection
    db = SerpAPIDatabase('DB/Main_DB.db')
    
    try:
        # Check if database exists and has tables
        conn = db.get_connection()
        cursor = conn.cursor()
        
        print("=" * 60)
        print("🛫 SerpAPI Flight Database Query")
        print("=" * 60)
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📊 Available tables: {[table[0] for table in tables]}")
        print()
        
        # Check flight_searches table
        try:
            cursor.execute("SELECT COUNT(*) FROM flight_searches")
            search_count = cursor.fetchone()[0]
            print(f"🔍 Flight Searches: {search_count} records")
            
            if search_count > 0:
                cursor.execute("""
                    SELECT search_id, departure_airport_code, arrival_airport_code, 
                           outbound_date, return_date, adults, total_results, 
                           created_at 
                    FROM flight_searches 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """)
                searches = cursor.fetchall()
                print(f"📋 Recent Flight Searches ({len(searches)} shown):")
                for search in searches:
                    route = f"{search[1]} → {search[2]}"
                    dates = f"{search[3]}" + (f" to {search[4]}" if search[4] else "")
                    print(f"   • {search[0]}: {route}, {dates}, {search[5]} adults, {search[6]} results")
                print()
        except Exception as e:
            print(f"⚠️ flight_searches table error: {e}")
        
        # Check flight_results table
        try:
            cursor.execute("SELECT COUNT(*) FROM flight_results")
            results_count = cursor.fetchone()[0]
            print(f"✈️ Flight Results: {results_count} records")
            
            if results_count > 0:
                cursor.execute("""
                    SELECT fr.search_id, fr.result_type, fr.total_price, 
                           fr.price_currency, fr.total_duration, fr.layover_count,
                           fs.departure_airport_code, fs.arrival_airport_code
                    FROM flight_results fr
                    JOIN flight_searches fs ON fr.search_id = fs.search_id
                    ORDER BY fr.created_at DESC 
                    LIMIT 10
                """)
                results = cursor.fetchall()
                print(f"📋 Recent Flight Results ({len(results)} shown):")
                for result in results:
                    route = f"{result[6]} → {result[7]}"
                    duration_hrs = result[4] // 60 if result[4] else 0
                    duration_mins = result[4] % 60 if result[4] else 0
                    stops = f", {result[5]} stops" if result[5] > 0 else ", nonstop"
                    print(f"   • {route}: {result[2]} {result[3]}, {duration_hrs}h {duration_mins}m{stops} ({result[1]})")
                print()
        except Exception as e:
            print(f"⚠️ flight_results table error: {e}")
        
        # Check flight_segments table
        try:
            cursor.execute("SELECT COUNT(*) FROM flight_segments")
            segments_count = cursor.fetchone()[0]
            print(f"🛩️ Flight Segments: {segments_count} records")
            
            if segments_count > 0:
                cursor.execute("""
                    SELECT fs.departure_airport_code, fs.arrival_airport_code, 
                           fs.airline_code, fs.flight_number, fs.departure_time,
                           fs.arrival_time, fs.duration_minutes
                    FROM flight_segments fs
                    ORDER BY fs.created_at DESC 
                    LIMIT 5
                """)
                segments = cursor.fetchall()
                print(f"📋 Recent Flight Segments ({len(segments)} shown):")
                for segment in segments:
                    duration_hrs = segment[6] // 60 if segment[6] else 0
                    duration_mins = segment[6] % 60 if segment[6] else 0
                    print(f"   • {segment[2]}{segment[3]}: {segment[0]} → {segment[1]}, {segment[4]} - {segment[5]} ({duration_hrs}h {duration_mins}m)")
                print()
        except Exception as e:
            print(f"⚠️ flight_segments table error: {e}")
        
        # Check airlines table
        try:
            cursor.execute("SELECT COUNT(*) FROM airlines")
            airlines_count = cursor.fetchone()[0]
            print(f"🏢 Airlines: {airlines_count} records")
            
            if airlines_count > 0:
                cursor.execute("SELECT airline_code, airline_name FROM airlines LIMIT 10")
                airlines = cursor.fetchall()
                print(f"📋 Airlines in Database ({len(airlines)} shown):")
                for airline in airlines:
                    print(f"   • {airline[0]}: {airline[1]}")
                print()
        except Exception as e:
            print(f"⚠️ airlines table error: {e}")
        
        # Check airports table
        try:
            cursor.execute("SELECT COUNT(*) FROM airports")
            airports_count = cursor.fetchone()[0]
            print(f"🛫 Airports: {airports_count} records")
            
            if airports_count > 0:
                cursor.execute("SELECT airport_code, airport_name, city, country FROM airports LIMIT 10")
                airports = cursor.fetchall()
                print(f"📋 Airports in Database ({len(airports)} shown):")
                for airport in airports:
                    print(f"   • {airport[0]}: {airport[1]}, {airport[2]}, {airport[3]}")
                print()
        except Exception as e:
            print(f"⚠️ airports table error: {e}")
        
        # Check api_queries table (original data storage)
        try:
            cursor.execute("SELECT COUNT(*) FROM api_queries")
            api_count = cursor.fetchone()[0]
            print(f"📡 API Queries: {api_count} records")
            
            if api_count > 0:
                cursor.execute("""
                    SELECT id, query_type, search_term, status_code, 
                           response_size, created_at 
                    FROM api_queries 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)
                queries = cursor.fetchall()
                print(f"📋 Recent API Queries ({len(queries)} shown):")
                for query in queries:
                    size_kb = query[4] / 1024 if query[4] else 0
                    print(f"   • ID {query[0]}: {query[1]} '{query[2]}' → {query[3]} ({size_kb:.1f}KB) at {query[5]}")
                print()
        except Exception as e:
            print(f"⚠️ api_queries table error: {e}")
        
        # Get database statistics
        try:
            stats = db.get_database_stats()
            print("📊 Database Summary:")
            print(f"   • Total API queries: {stats.get('total_records', 0)}")
            if 'records_by_type' in stats:
                for query_type, count in stats['records_by_type'].items():
                    print(f"   • {query_type}: {count} queries")
            
            if 'date_range' in stats and stats['date_range']['earliest']:
                print(f"   • Data range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
        except Exception as e:
            print(f"⚠️ Statistics error: {e}")
        
        print("=" * 60)
        print("✅ Database query completed successfully")
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print("💡 Make sure Main_DB.db exists in the DB directory")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    query_all_flights()
