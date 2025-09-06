"""
Test Database Storage Fix
========================
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_flight_search import EnhancedFlightSearchClient

def test_database_storage():
    """Test that flight data is properly stored in database"""
    
    print("🔍 Testing Database Storage Fix...")
    
    client = EnhancedFlightSearchClient()
    
    # Test with a new route to ensure it's not cached
    result = client.search_flights(
        departure_id='SYD',
        arrival_id='LAX',
        outbound_date='2025-12-01'
        # Return date will be auto-generated
    )
    
    print(f"Search completed: {result.get('success')}")
    print(f"Source: {result.get('source')}")
    
    # Check database immediately after
    if result.get('success'):
        import sqlite3
        db_path = "C:\\Users\\MY PC\\SerpAPI\\DB\\Main_DB.db"
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check flight_searches table
        cursor.execute("SELECT COUNT(*) FROM flight_searches")
        searches_count = cursor.fetchone()[0]
        print(f"Flight searches in DB: {searches_count}")
        
        # Check flight_results table  
        cursor.execute("SELECT COUNT(*) FROM flight_results")
        results_count = cursor.fetchone()[0]
        print(f"Flight results in DB: {results_count}")
        
        # Show latest search
        cursor.execute("SELECT search_id, departure_id, arrival_id, outbound_date, return_date FROM flight_searches ORDER BY created_at DESC LIMIT 1")
        latest = cursor.fetchone()
        if latest:
            print(f"Latest search: {latest[0]} - {latest[1]} → {latest[2]} ({latest[3]} to {latest[4]})")
        
        conn.close()

if __name__ == "__main__":
    test_database_storage()
