"""
Real Flight Search Test: POM to MNL
Tests actual SerpAPI Google Flights search with real data
Security: Uses environment variable for API key only
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))

from enhanced_flight_search import EnhancedFlightSearchClient
from flight_processor import FlightDataProcessor

def test_real_flight_search():
    """Test real flight search POM to MNL"""
    
    print("🛩️ REAL FLIGHT SEARCH TEST")
    print("=" * 50)
    print("Route: POM (Port Moresby) → MNL (Manila)")
    print("Date: September 26, 2025")
    print("Security: Using environment variable API key")
    print("=" * 50)
    
    try:
        # Initialize secure client
        client = EnhancedFlightSearchClient()
        processor = FlightDataProcessor()
        
        print("✅ Enhanced flight search client initialized securely")
        
        # Search parameters
        search_params = {
            'departure_id': 'POM',
            'arrival_id': 'MNL', 
            'outbound_date': '2025-09-26',
            'adults': 1,
            'travel_class': 1,  # Economy
            'currency': 'USD'
        }
        
        print(f"\n🔍 Searching flights...")
        print(f"   From: {search_params['departure_id']}")
        print(f"   To: {search_params['arrival_id']}")
        print(f"   Date: {search_params['outbound_date']}")
        print(f"   Passengers: {search_params['adults']} adult(s)")
        
        # Perform search (will check cache first, then API)
        result = client.search_flights(**search_params)
        
        print(f"\n📊 SEARCH RESULTS:")
        print(f"   Success: {result['success']}")
        print(f"   Source: {result['source'].upper()}")
        
        if result['success']:
            print(f"   Message: {result['message']}")
            
            # Get data
            search_data = result['data']
            print(f"   Search ID: {search_data.get('search_id', 'N/A')}")
            
            if result['source'] == 'cache':
                cache_age = result.get('cache_age_hours', 0)
                print(f"   Cache Age: {cache_age:.2f} hours")
            
            # Process and store data if from API
            if result['source'] == 'api' and 'raw_response' in search_data:
                print(f"\n💾 Processing and storing flight data...")
                
                try:
                    processing_result = processor.process_search_response(search_data)
                    print(f"   ✅ Data processed: {processing_result.get('message', 'Success')}")
                    
                    # Show some results if available
                    if 'best_flights' in search_data.get('raw_response', {}):
                        best_flights = search_data['raw_response']['best_flights']
                        print(f"   📈 Found {len(best_flights)} flight option(s)")
                        
                        for i, flight in enumerate(best_flights[:3], 1):  # Show first 3
                            price = flight.get('price', 'N/A')
                            duration = flight.get('total_duration', 'N/A')
                            print(f"      Flight {i}: ${price} - {duration} min")
                    
                except Exception as e:
                    print(f"   ⚠️ Processing error: {e}")
            
            elif result['source'] == 'cache':
                print(f"\n📋 Using cached flight data (no processing needed)")
                if 'flight_results_count' in result['data']:
                    count = result['data']['flight_results_count']
                    print(f"   📈 Cached results: {count} flight option(s)")
        
        else:
            print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
            if result['source'] == 'api_error':
                print(f"   💡 This might be due to route availability or API limits")
        
        # Show cache statistics
        print(f"\n📊 CACHE STATISTICS:")
        try:
            stats = client.get_cache_stats()
            if 'error' not in stats:
                print(f"   Total searches: {stats['total_cached_searches']}")
                print(f"   Recent (24h): {stats['recent_searches_24h']}")
                if stats['popular_routes']:
                    print(f"   Popular routes: {[r['route'] for r in stats['popular_routes'][:3]]}")
            else:
                print(f"   Error: {stats['error']}")
        except Exception as e:
            print(f"   Error getting stats: {e}")
        
        print(f"\n🎯 Flight search test completed!")
        return result['success']
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_flight_search()
    if success:
        print("\n✅ Real flight search test successful!")
    else:
        print("\n❌ Flight search test failed!")
