"""
Flight Search Diagnostic Test
Tests with common route first, then POM-MNL
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Main'))

from enhanced_flight_search import EnhancedFlightSearchClient

def diagnostic_test():
    """Run diagnostic tests on flight search"""
    
    print("🔧 FLIGHT SEARCH DIAGNOSTIC")
    print("=" * 40)
    
    try:
        client = EnhancedFlightSearchClient()
        print("✅ Client initialized")
        print(f"✅ API client available: {bool(client.api_client)}")
        
        # Test 1: Common route (LAX to JFK)
        print(f"\n🧪 TEST 1: Common Route (LAX → JFK)")
        result1 = client.search_flights(
            departure_id='LAX',
            arrival_id='JFK',
            outbound_date='2025-09-26',
            adults=1
        )
        
        print(f"   Success: {result1['success']}")
        print(f"   Source: {result1['source']}")
        if not result1['success']:
            print(f"   Error: {result1.get('error', 'No error message')}")
        
        # Test 2: POM to MNL route  
        print(f"\n🧪 TEST 2: POM → MNL Route")
        result2 = client.search_flights(
            departure_id='POM',
            arrival_id='MNL',
            outbound_date='2025-09-26',
            adults=1
        )
        
        print(f"   Success: {result2['success']}")
        print(f"   Source: {result2['source']}")
        if not result2['success']:
            print(f"   Error: {result2.get('error', 'No error message')}")
            
        # Test 3: Check environment variable
        print(f"\n🔑 API Key Check:")
        import os
        api_key = os.environ.get('SERPAPI_KEY')
        if api_key:
            print(f"   ✅ Environment variable set: {api_key[:16]}...{api_key[-4:]}")
        else:
            print(f"   ❌ Environment variable not found")
            
        return result1['success'] or result2['success']
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    diagnostic_test()
