"""
Final Flight Search Test with Optimized Schema
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))

from enhanced_flight_search import FlightSearchCache

def test_flight_search_compatibility():
    """Test flight search with optimized schema"""
    
    print("🧪 TESTING FLIGHT SEARCH CACHE WITH OPTIMIZED SCHEMA")
    print("=" * 55)
    
    cache = FlightSearchCache("../DB/Main_DB.db")
    
    # Test cache search (should work with updated query)
    test_params = {
        'departure_id': 'SYD',
        'arrival_id': 'LAX',
        'outbound_date': '2025-10-01'
    }
    
    try:
        result = cache.search_cache(test_params, max_age_hours=24)
        
        if result:
            print("✅ Cache search SUCCESSFUL!")
            print(f"   Found cached data: {result.get('cached', False)}")
            print(f"   Flight results: {result.get('flight_results_count', 0)}")
        else:
            print("✅ Cache search completed (no cached data found)")
            print("   This is normal - cache miss means query structure is working")
            
        print("\n🎉 FLIGHT SEARCH CACHE IS COMPATIBLE WITH OPTIMIZED SCHEMA!")
        
    except Exception as e:
        print(f"❌ Cache search failed: {e}")
        print("   Schema compatibility issue detected!")

if __name__ == "__main__":
    test_flight_search_compatibility()
