"""
Flight Search Test: POM to MNL on September 26
==============================================
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_flight_search import EnhancedFlightSearchClient

def search_pom_mnl():
    """Search for flights from POM to MNL on September 26, 2025"""
    
    print("🔍 FLIGHT SEARCH: POM → MNL on September 26, 2025")
    print("=" * 60)
    
    # Initialize the enhanced flight search client
    client = EnhancedFlightSearchClient()
    
    print("Searching for flights...")
    print("Route: Port Moresby (POM) → Manila (MNL)")
    print("Date: September 26, 2025")
    print("Passengers: 1 Adult")
    print("Class: Economy")
    print()
    
    # Perform the search
    # This will first check cache, then prompt for approval if API call needed
    result = client.search_flights(
        departure_id='POM',
        arrival_id='MNL',
        outbound_date='2025-09-26',
        adults=1,
        currency='USD'
    )
    
    # Display results
    print("\n" + "=" * 60)
    print("📊 SEARCH RESULTS")
    print("=" * 60)
    
    print(f"✅ Success: {result.get('success')}")
    print(f"📍 Data Source: {result.get('source')}")
    
    if result.get('success'):
        data = result.get('data', {})
        
        # Display flight information
        if 'best_flights' in data:
            flights = data['best_flights']
            print(f"🛫 Found {len(flights)} best flight options:")
            print()
            
            for i, flight in enumerate(flights, 1):
                print(f"Option {i}:")
                
                if 'flights' in flight and flight['flights']:
                    flight_leg = flight['flights'][0]
                    airline = flight_leg.get('airline', 'Unknown')
                    flight_num = flight_leg.get('flight_number', 'N/A')
                    dep_time = flight_leg.get('departure_airport', {}).get('time', 'N/A')
                    arr_time = flight_leg.get('arrival_airport', {}).get('time', 'N/A')
                    aircraft = flight_leg.get('airplane', 'N/A')
                    
                    print(f"   🏢 Airline: {airline} ({flight_num})")
                    print(f"   🛫 Departure: {dep_time}")
                    print(f"   🛬 Arrival: {arr_time}")
                    print(f"   ✈️  Aircraft: {aircraft}")
                
                price = flight.get('price', 'N/A')
                duration = flight.get('total_duration', 0)
                hours = duration // 60 if duration else 0
                minutes = duration % 60 if duration else 0
                
                print(f"   💰 Price: ${price} USD")
                print(f"   ⏱️  Duration: {hours}h {minutes}m")
                
                if 'carbon_emissions' in flight:
                    emissions = flight['carbon_emissions']
                    co2_kg = emissions.get('this_flight', 0) / 1000  # Convert to kg
                    print(f"   🌱 CO2: {co2_kg:.0f} kg")
                
                print()
        
        # Display other flights if available
        if 'other_flights' in data and data['other_flights']:
            other_flights = data['other_flights']
            print(f"🔄 Also found {len(other_flights)} other flight options")
            
            # Show cheapest other option
            if other_flights:
                cheapest_other = min(other_flights, key=lambda x: x.get('price', float('inf')))
                print(f"   Cheapest alternative: ${cheapest_other.get('price', 'N/A')} USD")
        
        # Display price insights
        if 'price_insights' in data:
            insights = data['price_insights']
            lowest = insights.get('lowest_price', 'N/A')
            level = insights.get('price_level', 'unknown')
            print(f"\n💡 Price Insights:")
            print(f"   Lowest available: ${lowest} USD")
            print(f"   Price level: {level}")
    
    else:
        error = result.get('error', 'Unknown error')
        print(f"❌ Search failed: {error}")
    
    print("\n" + "=" * 60)
    print("✅ Search Complete")
    print("=" * 60)

if __name__ == "__main__":
    search_pom_mnl()
