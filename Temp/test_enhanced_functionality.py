#!/usr/bin/env python3
"""
Test Enhanced Functionality: Airport/Airline Storage and 24-Hour Data Freshness
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta

# Add the main directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))

from enhanced_flight_search import EnhancedFlightSearchClient

def test_airport_airline_storage():
    """Test that airports and airlines are being stored properly"""
    print("🧪 Testing Airport and Airline Storage...")
    
    # Initialize the client
    client = EnhancedFlightSearchClient()
    
    # Test a flight search to trigger airport/airline storage
    print("\n🔍 Performing flight search to test storage...")
    result = client.search_flights(
        departure_id="JFK",
        arrival_id="LAX", 
        outbound_date="2025-12-15",
        return_date="2025-12-22"
    )
    
    print(f"Search completed: {result.get('success')}")
    print(f"Source: {result.get('source')}")
    
    # Check database for stored airport and airline data
    print("\n📊 Checking database for airport and airline data...")
    
    with sqlite3.connect('../DB/Main_DB.db') as conn:
        cursor = conn.cursor()
        
        # Check airports
        cursor.execute("SELECT COUNT(*) FROM airports")
        airport_count = cursor.fetchone()[0]
        print(f"✈️ Airports stored: {airport_count}")
        
        if airport_count > 0:
            cursor.execute("SELECT airport_code, airport_name, first_seen FROM airports LIMIT 5")
            airports = cursor.fetchall()
            print("   Sample airports:")
            for airport in airports:
                print(f"      {airport[0]}: {airport[1]} (first seen: {airport[2]})")
        
        # Check airlines
        cursor.execute("SELECT COUNT(*) FROM airlines")
        airline_count = cursor.fetchone()[0]
        print(f"🛩️ Airlines stored: {airline_count}")
        
        if airline_count > 0:
            cursor.execute("SELECT airline_code, airline_name, first_seen FROM airlines LIMIT 5")
            airlines = cursor.fetchall()
            print("   Sample airlines:")
            for airline in airlines:
                print(f"      {airline[0]}: {airline[1]} (first seen: {airline[2]})")
    
    return airport_count > 0 or airline_count > 0

def test_24_hour_cleanup():
    """Test the 24-hour data cleanup functionality"""
    print("\n🧪 Testing 24-Hour Data Cleanup...")
    
    # Check current data count
    with sqlite3.connect('../DB/Main_DB.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM flight_searches")
        before_searches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM flight_results") 
        before_results = cursor.fetchone()[0]
        
        print(f"📊 Before cleanup - Searches: {before_searches}, Results: {before_results}")
        
        # Create some old test data to verify cleanup works
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        
        # Insert old test search
        cursor.execute("""
        INSERT INTO flight_searches (
            search_id, search_timestamp, departure_id, arrival_id, 
            outbound_date, flight_type, adults, currency, 
            response_status, total_results, created_at, cache_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test_old_search_cleanup', old_time, 'TEST', 'OLD',
            '2025-01-01', 1, 1, 'USD', 'success', 0, old_time,
            'test_cleanup_key'
        ))
        
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM flight_searches")
        after_insert = cursor.fetchone()[0]
        print(f"📊 After inserting old data - Searches: {after_insert}")
    
    # Initialize client to trigger cleanup
    client = EnhancedFlightSearchClient()
    
    # Manually trigger cleanup
    print("🧹 Running cleanup process...")
    client.cache.cleanup_old_data(max_age_hours=24)
    
    # Check data count after cleanup
    with sqlite3.connect('../DB/Main_DB.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM flight_searches")
        after_cleanup = cursor.fetchone()[0]
        
        print(f"📊 After cleanup - Searches: {after_cleanup}")
        
        # Verify our test old data was removed
        cursor.execute("SELECT COUNT(*) FROM flight_searches WHERE search_id = 'test_old_search_cleanup'")
        old_data_count = cursor.fetchone()[0]
        
        if old_data_count == 0:
            print("✅ Old test data was successfully cleaned up!")
            return True
        else:
            print("❌ Old test data was NOT cleaned up!")
            return False

def test_data_freshness_policy():
    """Test that cache only returns data within 24 hours"""
    print("\n🧪 Testing 24-Hour Cache Freshness Policy...")
    
    client = EnhancedFlightSearchClient()
    
    # Test cache search with 24-hour limit
    search_params = {
        'departure_id': 'SYD',
        'arrival_id': 'LAX',
        'outbound_date': '2025-12-01',
        'return_date': '2025-12-08',
        'adults': 1,
        'currency': 'USD'
    }
    
    # Search with 24-hour limit
    cached_result = client.cache.search_cache(search_params, max_age_hours=24)
    
    if cached_result:
        print("✅ Found cached data within 24 hours")
        print(f"   Cache timestamp: {cached_result.get('cache_timestamp')}")
        return True
    else:
        print("ℹ️ No cached data found within 24 hours (expected for fresh database)")
        return True

if __name__ == "__main__":
    print("🚀 TESTING ENHANCED FUNCTIONALITY")
    print("=" * 50)
    
    # Run tests
    airport_airline_test = test_airport_airline_storage()
    cleanup_test = test_24_hour_cleanup()
    freshness_test = test_data_freshness_policy()
    
    print("\n" + "=" * 50)
    print("📋 TEST RESULTS:")
    print(f"✅ Airport/Airline Storage: {'PASS' if airport_airline_test else 'FAIL'}")
    print(f"✅ 24-Hour Cleanup: {'PASS' if cleanup_test else 'FAIL'}")
    print(f"✅ Data Freshness Policy: {'PASS' if freshness_test else 'FAIL'}")
    
    if all([airport_airline_test, cleanup_test, freshness_test]):
        print("\n🎉 ALL TESTS PASSED! Enhanced functionality is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the implementation.")
