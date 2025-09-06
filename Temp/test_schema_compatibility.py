"""
Test Database Schema Compatibility
Check if flight search functions work with optimized schema
"""

import sqlite3
import json
import sys
import os
from datetime import datetime

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'DB'))

def test_schema_compatibility():
    """Test if current flight search code works with optimized schema"""
    db_path = "../DB/Main_DB.db"
    
    print("🔍 TESTING DATABASE SCHEMA COMPATIBILITY")
    print("=" * 50)
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check current schema structure
        print("\n📋 CURRENT SCHEMA STRUCTURE:")
        
        # Check flight_segments table structure
        cursor.execute("PRAGMA table_info(flight_segments)")
        fs_columns = [row[1] for row in cursor.fetchall()]
        print(f"   flight_segments columns: {fs_columns}")
        
        # Check airports table structure
        cursor.execute("PRAGMA table_info(airports)")
        airports_columns = [row[1] for row in cursor.fetchall()]
        print(f"   airports columns: {airports_columns}")
        
        # Check airlines table structure
        cursor.execute("PRAGMA table_info(airlines)")
        airlines_columns = [row[1] for row in cursor.fetchall()]
        print(f"   airlines columns: {airlines_columns}")
        
        # Test problematic query from enhanced_flight_search.py
        print("\n🧪 TESTING CACHE QUERY COMPATIBILITY:")
        
        try:
            # This query is from line 95-99 in enhanced_flight_search.py
            problematic_query = """
            SELECT fr.*, fs_segments.departure_airport, fs_segments.arrival_airport,
                   fs_segments.departure_time, fs_segments.arrival_time,
                   fs_segments.duration, fs_segments.airline_code
            FROM flight_results fr
            LEFT JOIN flight_segments fs_segments ON fr.result_id = fs_segments.result_id
            WHERE fr.search_id = 'test'
            ORDER BY fr.price ASC
            """
            
            cursor.execute(problematic_query)
            print("   ❌ PROBLEM: Query uses old column names that don't exist!")
            print("      - departure_airport (should be departure_airport_code)")
            print("      - arrival_airport (should be arrival_airport_code)")
            print("      - duration (should be duration_minutes)")
            
        except sqlite3.OperationalError as e:
            print(f"   ❌ QUERY FAILED: {e}")
            print("      This confirms the schema incompatibility!")
        
        # Test correct query with optimized schema
        print("\n✅ TESTING CORRECTED QUERY:")
        
        try:
            corrected_query = """
            SELECT fr.id, fr.price, fr.currency, 
                   fs.departure_airport_code, da.airport_name as dep_name,
                   fs.arrival_airport_code, aa.airport_name as arr_name,
                   fs.departure_time, fs.arrival_time, fs.duration_minutes,
                   fs.airline_code, al.airline_name
            FROM flight_results fr
            LEFT JOIN flight_segments fs ON fr.result_id = fs.flight_result_id
            LEFT JOIN airports da ON fs.departure_airport_code = da.airport_code
            LEFT JOIN airports aa ON fs.arrival_airport_code = aa.airport_code
            LEFT JOIN airlines al ON fs.airline_code = al.airline_code
            LIMIT 3
            """
            
            cursor.execute(corrected_query)
            results = cursor.fetchall()
            
            print(f"   ✅ CORRECTED QUERY WORKS! Found {len(results)} results")
            
            for result in results:
                print(f"      Flight: {result['dep_name']} → {result['arr_name']}")
                print(f"      Price: {result['currency']} {result['price']}")
                print(f"      Airline: {result['airline_name']} ({result['airline_code']})")
                print()
                
        except sqlite3.OperationalError as e:
            print(f"   ❌ CORRECTED QUERY FAILED: {e}")
        
        # Check if layovers table is compatible
        print("\n🔍 TESTING LAYOVERS TABLE COMPATIBILITY:")
        
        try:
            layover_query = """
            SELECT l.*, a.airport_name
            FROM layovers l
            LEFT JOIN airports a ON l.airport_code = a.airport_code
            LIMIT 3
            """
            
            cursor.execute(layover_query)
            layovers = cursor.fetchall()
            
            print(f"   ✅ LAYOVERS QUERY WORKS! Found {len(layovers)} layovers")
            for layover in layovers:
                print(f"      Layover at: {layover['airport_name']} ({layover['airport_code']})")
                print(f"      Duration: {layover['duration_minutes']} minutes")
                
        except sqlite3.OperationalError as e:
            print(f"   ❌ LAYOVERS QUERY FAILED: {e}")

if __name__ == "__main__":
    test_schema_compatibility()
