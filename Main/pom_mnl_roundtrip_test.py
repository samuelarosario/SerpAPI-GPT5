"""
POM to MNL Round-Trip Search Test
=================================

Testing the new round-trip default behavior with POM to MNL route.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_flight_search import EnhancedFlightSearchClient

def search_pom_mnl_roundtrip():
    """Search POM to MNL with round-trip default"""
    
    print("🔍 POM → MNL ROUND-TRIP SEARCH (Enhanced Data Capture)")
    print("=" * 65)
    print("Testing new round-trip default for comprehensive flight data")
    print()
    
    client = EnhancedFlightSearchClient()
    
    print("Route: Port Moresby (POM) → Manila (MNL)")
    print("Outbound: September 26, 2025")
    print("Return: Auto-generated (7 days later = October 3, 2025)")
    print("Search Type: Round-trip (for enhanced data capture)")
    print()
    
    # Search with auto-generated return date
    result = client.search_flights(
        departure_id='POM',
        arrival_id='MNL',
        outbound_date='2025-09-26'
        # No return date - system will auto-generate 2025-10-03
    )
    
    print("=" * 65)
    print("📊 ENHANCED SEARCH RESULTS")
    print("=" * 65)
    
    print(f"✅ Success: {result.get('success')}")
    print(f"📍 Source: {result.get('source')}")
    
    if result.get('success'):
        data = result.get('data', {})
        
        # Show search parameters used
        search_params = data.get('search_parameters', {})
        if search_params:
            outbound = search_params.get('outbound_date', 'N/A')
            return_date = search_params.get('return_date', 'N/A')
            trip_type = search_params.get('type', 'unknown')
            
            print(f"\n🔧 Search Parameters Used:")
            print(f"   Outbound Date: {outbound}")
            print(f"   Return Date: {return_date}")
            print(f"   Trip Type: {trip_type} ({'Round-trip' if trip_type == '1' else 'One-way' if trip_type == '2' else 'Unknown'})")
        
        # Display outbound flights
        if 'best_flights' in data:
            flights = data['best_flights']
            print(f"\n🛫 OUTBOUND FLIGHTS: {len(flights)} options found")
            
            for i, flight in enumerate(flights[:3], 1):  # Show top 3
                if 'flights' in flight and flight['flights']:
                    flight_leg = flight['flights'][0]
                    airline = flight_leg.get('airline', 'Unknown')
                    flight_num = flight_leg.get('flight_number', 'N/A')
                    dep_time = flight_leg.get('departure_airport', {}).get('time', 'N/A')
                    arr_time = flight_leg.get('arrival_airport', {}).get('time', 'N/A')
                
                price = flight.get('price', 'N/A')
                duration = flight.get('total_duration', 0)
                hours = duration // 60 if duration else 0
                minutes = duration % 60 if duration else 0
                
                print(f"   {i}. {airline} {flight_num} - ${price} USD")
                print(f"      {dep_time} → {arr_time} ({hours}h {minutes}m)")
        
        # Look for return flight information
        # Note: SerpAPI may include return flights in the response for round-trip searches
        if 'other_flights' in data:
            other_count = len(data['other_flights'])
            print(f"\n🔄 ADDITIONAL OPTIONS: {other_count} alternative routes")
            
        # Price insights
        if 'price_insights' in data:
            insights = data['price_insights']
            lowest = insights.get('lowest_price', 'N/A')
            level = insights.get('price_level', 'unknown')
            
            print(f"\n💰 PRICING INSIGHTS:")
            print(f"   Lowest Price: ${lowest} USD")
            print(f"   Price Level: {level}")
            
            if 'typical_price_range' in insights:
                price_range = insights['typical_price_range']
                print(f"   Typical Range: ${price_range[0]} - ${price_range[1]} USD")
    
    else:
        error = result.get('error', 'Unknown error')
        print(f"❌ Search failed: {error}")
    
    print("\n" + "=" * 65)
    print("✅ ENHANCED DATA CAPTURE COMPLETE")
    print("=" * 65)
    print("Benefits of round-trip search:")
    print("• More comprehensive flight options")
    print("• Better understanding of route pricing")
    print("• Return flight availability information")
    print("• Enhanced planning capabilities")

if __name__ == "__main__":
    search_pom_mnl_roundtrip()
