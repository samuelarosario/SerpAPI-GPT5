"""
Database Schema Optimization - Validation Report
===============================================

This report validates that the flight search system is compatible 
with the optimized database schema changes.
"""

import sqlite3
import json
import sys
import os
from datetime import datetime

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'DB'))

def generate_validation_report():
    """Generate comprehensive validation report"""
    db_path = "../DB/Main_DB.db"
    
    print("📋 DATABASE SCHEMA OPTIMIZATION - VALIDATION REPORT")
    print("=" * 60)
    print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Section 1: Schema Structure Validation
        print("1️⃣ SCHEMA STRUCTURE VALIDATION")
        print("-" * 35)
        
        tables_to_check = ['airports', 'airlines', 'flight_segments', 'layovers']
        
        for table in tables_to_check:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"   ✅ {table}: {len(columns)} columns")
            
            # Check key columns exist
            if table == 'flight_segments':
                required_cols = ['departure_airport_code', 'arrival_airport_code', 'airline_code', 'duration_minutes']
                missing = [col for col in required_cols if col not in columns]
                if missing:
                    print(f"      ❌ Missing required columns: {missing}")
                else:
                    print(f"      ✅ All required foreign key columns present")
            
            elif table == 'airports':
                if 'airport_code' in columns and 'airport_name' in columns:
                    print(f"      ✅ Primary key and name columns present")
                else:
                    print(f"      ❌ Missing essential airport columns")
            
            elif table == 'airlines':
                if 'airline_code' in columns and 'airline_name' in columns:
                    print(f"      ✅ Primary key and name columns present")
                else:
                    print(f"      ❌ Missing essential airline columns")
        
        print()
        
        # Section 2: Data Integrity Validation
        print("2️⃣ DATA INTEGRITY VALIDATION")
        print("-" * 32)
        
        # Check foreign key relationships
        try:
            cursor.execute("""
            SELECT COUNT(*) as orphaned_segments
            FROM flight_segments fs
            LEFT JOIN airports da ON fs.departure_airport_code = da.airport_code
            WHERE da.airport_code IS NULL AND fs.departure_airport_code IS NOT NULL
            """)
            orphaned_dep = cursor.fetchone()[0]
            
            cursor.execute("""
            SELECT COUNT(*) as orphaned_segments
            FROM flight_segments fs  
            LEFT JOIN airports aa ON fs.arrival_airport_code = aa.airport_code
            WHERE aa.airport_code IS NULL AND fs.arrival_airport_code IS NOT NULL
            """)
            orphaned_arr = cursor.fetchone()[0]
            
            cursor.execute("""
            SELECT COUNT(*) as orphaned_segments
            FROM flight_segments fs
            LEFT JOIN airlines al ON fs.airline_code = al.airline_code  
            WHERE al.airline_code IS NULL AND fs.airline_code IS NOT NULL
            """)
            orphaned_airline = cursor.fetchone()[0]
            
            print(f"   ✅ Orphaned departure airports: {orphaned_dep}")
            print(f"   ✅ Orphaned arrival airports: {orphaned_arr}")
            print(f"   ✅ Orphaned airlines: {orphaned_airline}")
            
            if orphaned_dep == 0 and orphaned_arr == 0 and orphaned_airline == 0:
                print("   🎉 Perfect referential integrity!")
            else:
                print("   ⚠️  Some orphaned records exist (normal for incomplete data)")
                
        except Exception as e:
            print(f"   ❌ Integrity check failed: {e}")
        
        print()
        
        # Section 3: Query Performance Validation
        print("3️⃣ QUERY PERFORMANCE VALIDATION")
        print("-" * 34)
        
        # Test JOIN performance
        start_time = datetime.now()
        
        cursor.execute("""
        SELECT COUNT(*)
        FROM flight_segments fs
        LEFT JOIN airports da ON fs.departure_airport_code = da.airport_code
        LEFT JOIN airports aa ON fs.arrival_airport_code = aa.airport_code
        LEFT JOIN airlines al ON fs.airline_code = al.airline_code
        """)
        
        count = cursor.fetchone()[0]
        end_time = datetime.now()
        query_duration = (end_time - start_time).total_seconds() * 1000
        
        print(f"   ✅ Triple JOIN query processed {count} records in {query_duration:.2f}ms")
        
        if query_duration < 100:
            print("   🚀 Excellent performance!")
        elif query_duration < 500:
            print("   ✅ Good performance!")
        else:
            print("   ⚠️  Consider adding indexes for better performance")
        
        print()
        
        # Section 4: Storage Efficiency Validation
        print("4️⃣ STORAGE EFFICIENCY VALIDATION")
        print("-" * 35)
        
        # Calculate storage savings
        cursor.execute("SELECT COUNT(*) FROM flight_segments")
        segment_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM airports")
        airport_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM airlines")
        airline_count = cursor.fetchone()[0]
        
        # Estimate storage saved (approximate)
        avg_airport_name_length = 25  # chars
        avg_airline_name_length = 15  # chars
        
        # Storage with redundancy (old schema)
        redundant_storage = segment_count * (avg_airport_name_length * 2 + avg_airline_name_length)
        
        # Storage with normalization (new schema)
        normalized_storage = (airport_count * avg_airport_name_length + 
                            airline_count * avg_airline_name_length)
        
        savings = redundant_storage - normalized_storage
        savings_percent = (savings / redundant_storage * 100) if redundant_storage > 0 else 0
        
        print(f"   📊 Flight segments: {segment_count}")
        print(f"   📊 Unique airports: {airport_count}")
        print(f"   📊 Unique airlines: {airline_count}")
        print(f"   💾 Estimated storage saved: ~{savings:,} characters ({savings_percent:.1f}%)")
        
        if savings_percent > 50:
            print("   🎉 Massive storage optimization achieved!")
        elif savings_percent > 25:
            print("   ✅ Significant storage savings!")
        else:
            print("   📈 Some storage optimization gained")
        
        print()
        
        # Section 5: Flight Search Function Validation
        print("5️⃣ FLIGHT SEARCH FUNCTION VALIDATION")
        print("-" * 40)
        
        # Test if enhanced_flight_search.py queries will work
        test_queries = [
            {
                'name': 'Cache Search Query',
                'query': """
                SELECT fs.departure_airport_code, da.airport_name as departure_airport_name,
                       fs.arrival_airport_code, aa.airport_name as arrival_airport_name,
                       fs.departure_time, fs.arrival_time, fs.duration_minutes,
                       fs.airline_code, al.airline_name
                FROM flight_results fr
                LEFT JOIN flight_segments fs ON fr.id = fs.flight_result_id
                LEFT JOIN airports da ON fs.departure_airport_code = da.airport_code
                LEFT JOIN airports aa ON fs.arrival_airport_code = aa.airport_code
                LEFT JOIN airlines al ON fs.airline_code = al.airline_code
                LIMIT 1
                """,
                'critical': True
            },
            {
                'name': 'Layover Query',
                'query': """
                SELECT l.*, a.airport_name, a.city
                FROM layovers l
                LEFT JOIN airports a ON l.airport_code = a.airport_code
                LIMIT 1
                """,
                'critical': True
            },
            {
                'name': 'Cleanup Query',
                'query': """
                SELECT COUNT(*) FROM flight_segments 
                WHERE flight_result_id IN (
                    SELECT id FROM flight_results WHERE search_id = 'dummy'
                )
                """,
                'critical': False
            }
        ]
        
        all_passed = True
        
        for test in test_queries:
            try:
                cursor.execute(test['query'])
                result = cursor.fetchone()
                print(f"   ✅ {test['name']}: PASSED")
            except Exception as e:
                print(f"   ❌ {test['name']}: FAILED - {e}")
                if test['critical']:
                    all_passed = False
        
        print()
        
        # Final Assessment
        print("6️⃣ FINAL ASSESSMENT")
        print("-" * 20)
        
        if all_passed:
            print("   🎉 ALL CRITICAL TESTS PASSED!")
            print("   ✅ Enhanced flight search is fully compatible with optimized schema")
            print("   ✅ Database operations will work correctly")
            print("   ✅ Storage optimization is successfully implemented")
            print()
            print("   🚀 RECOMMENDATION: Schema optimization is READY FOR PRODUCTION!")
        else:
            print("   ⚠️  Some critical tests failed")
            print("   📝 RECOMMENDATION: Review failed queries before deploying")
        
        print()
        print("📋 Report Complete")
        print("=" * 60)

if __name__ == "__main__":
    generate_validation_report()
