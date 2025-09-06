"""
Clear database and search POM to MNL on Sept 26
Using existing flight search system
"""
import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'DB'))

from enhanced_flight_search import EnhancedFlightSearchClient

def clear_and_search():
    """Clear database and perform fresh search"""
    
    print("🗑️ CLEARING DATABASE AND PERFORMING FRESH SEARCH")
    print("=" * 50)
    
    # Create flight search client
    client = EnhancedFlightSearchClient()
    
    # Clear old data using the cache cleanup method
    print("🧹 Clearing old cached data...")
    try:
        # Use cleanup method with 0 hours to delete everything
        client.cache.cleanup_old_data(max_age_hours=0)
        print("✅ Cache cleanup completed")
    except Exception as e:
        print(f"⚠️  Cache cleanup: {e}")
    
    # Perform fresh search for POM to MNL on Sept 26
    print("\n🔍 PERFORMING FRESH SEARCH: POM → MNL (2025-09-26)")
    print("=" * 55)
    
    result = client.search_flights(
        departure_id='POM',
        arrival_id='MNL', 
        outbound_date='2025-09-26'
    )
    
    print(f"\n✅ Search Status: {result.get('success', False)}")
    print(f"📊 Source: {result.get('source', 'unknown')}")
    print(f"🔄 Processing Status: {result.get('processing_status', 'unknown')}")
    
    if result.get('success'):
        flight_data = result.get('flight_data', {})
        best_flights = flight_data.get('best_flights', [])
        other_flights = flight_data.get('other_flights', [])
        
        total_flights = len(best_flights) + len(other_flights)
        print(f"✈️ Total flights found: {total_flights}")
        
        if best_flights:
            print("\n🏆 TOP 3 BEST FLIGHTS:")
            for i, flight in enumerate(best_flights[:3], 1):
                price = flight.get('price', 0)
                currency = flight.get('currency', 'USD')
                total_duration = flight.get('total_duration', 0)
                
                print(f"   {i}. {currency} {price} - {total_duration} minutes")
                
                flights = flight.get('flights', [])
                for segment in flights:
                    dep_airport = segment.get('departure_airport', {})
                    arr_airport = segment.get('arrival_airport', {})
                    airline = segment.get('airline', 'Unknown')
                    flight_num = segment.get('flight_number', 'N/A')
                    
                    print(f"      {dep_airport.get('id', '?')} → {arr_airport.get('id', '?')} ({airline} {flight_num})")
        
        print(f"\n💾 Fresh data stored in optimized database schema")
    else:
        print(f"❌ Search failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    clear_and_search()
