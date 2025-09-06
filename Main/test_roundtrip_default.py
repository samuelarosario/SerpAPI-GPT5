"""
Test Round-Trip Default Flight Search
=====================================

This script tests the new behavior where all flight searches default to 
round-trip to capture more comprehensive flight data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_flight_search import EnhancedFlightSearchClient

def test_roundtrip_default():
    """Test the round-trip default behavior"""
    
    print("🔍 TESTING: Round-Trip Default Flight Search")
    print("=" * 60)
    print("Testing enhanced data capture with automatic round-trip searches")
    print()
    
    client = EnhancedFlightSearchClient()
    
    # Test 1: Search without return date (should auto-generate)
    print("📋 TEST 1: Single date search (auto round-trip)")
    print("-" * 50)
    print("Searching POM → MNL on 2025-09-26 (no return date specified)")
    print("System should auto-generate return date and search round-trip")
    print()
    
    result1 = client.search_flights(
        departure_id='POM',
        arrival_id='MNL',
        outbound_date='2025-09-26'
        # No return_date specified - should auto-generate
    )
    
    print(f"✅ Success: {result1.get('success')}")
    print(f"📍 Source: {result1.get('source')}")
    
    if result1.get('success'):
        data1 = result1.get('data', {})
        
        # Check for outbound flights
        if 'best_flights' in data1:
            print(f"🛫 Found {len(data1['best_flights'])} outbound flight options")
            
            # Display first outbound option
            if data1['best_flights']:
                first_flight = data1['best_flights'][0]
                price = first_flight.get('price', 'N/A')
                print(f"   Best outbound: ${price} USD")
        
        # Check for return flights data
        search_params = data1.get('search_parameters', {})
        if 'outbound_date' in search_params and 'return_date' in search_params:
            print(f"🔄 Search included return flights:")
            print(f"   Outbound: {search_params.get('outbound_date')}")
            print(f"   Return: {search_params.get('return_date')}")
        
        # Look for return flight data in response
        if 'other_flights' in data1:
            print(f"📊 Additional flight data: {len(data1['other_flights'])} alternatives")
    
    print()
    
    # Test 2: Search with explicit return date
    print("📋 TEST 2: Explicit round-trip search")
    print("-" * 50)
    print("Searching LAX → JFK with explicit return date")
    print()
    
    result2 = client.search_flights(
        departure_id='LAX',
        arrival_id='JFK',
        outbound_date='2025-10-15',
        return_date='2025-10-22'  # Explicit return date
    )
    
    print(f"✅ Success: {result2.get('success')}")
    print(f"📍 Source: {result2.get('source')}")
    
    if result2.get('success'):
        data2 = result2.get('data', {})
        
        if 'best_flights' in data2:
            print(f"🛫 Found {len(data2['best_flights'])} flight options")
        
        search_params2 = data2.get('search_parameters', {})
        if search_params2:
            trip_type = search_params2.get('type', 'unknown')
            print(f"🔄 Trip type in API call: {trip_type} (1=round-trip, 2=one-way)")
    
    print()
    print("=" * 60)
    print("📊 SUMMARY: Enhanced Data Capture")
    print("=" * 60)
    
    print("✅ Benefits of round-trip default:")
    print("   • More comprehensive flight data")
    print("   • Better price comparison options")
    print("   • Return flight availability information")
    print("   • Enhanced route planning capabilities")
    print("   • Auto-generated return dates when not specified")
    print()
    
    print("🔧 How it works:")
    print("   • If no return date provided: auto-generates +7 days")
    print("   • Always searches round-trip for maximum data")
    print("   • Maintains cache efficiency")
    print("   • Same approval process applies")

if __name__ == "__main__":
    test_roundtrip_default()
