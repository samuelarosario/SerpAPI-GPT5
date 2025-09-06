#!/usr/bin/env python3
"""
Display POM → CDG flight results using the enhanced flight search system
"""

import sys
sys.path.append('Main')
from enhanced_flight_search import EnhancedFlightSearchClient

def display_pom_cdg_flights():
    """Display the POM → CDG flights using the correct search function"""
    
    print('🛫 Displaying POM → CDG Flights')
    print('Using: EnhancedFlightSearchClient.search_flights()')
    print('=' * 60)
    
    # Initialize the enhanced flight search client
    client = EnhancedFlightSearchClient()
    
    # Search for POM → CDG flights (this will use cache if available)
    try:
        results = client.search_flights(
            departure_id='POM',
            arrival_id='CDG', 
            outbound_date='2025-10-10'
        )
        
        if results['success']:
            print(f"✅ Search Status: {results['source'].upper()}")
            if results['source'] == 'cache':
                print(f"📅 Cache Age: {results.get('cache_age_hours', 0):.1f} hours")
            print()
            
            # Get the flight data
            flight_data = results['data']
            
            # Display best flights
            best_flights = flight_data.get('best_flights', [])
            if best_flights:
                print('⭐ BEST FLIGHTS:')
                for i, flight in enumerate(best_flights, 1):
                    price = flight.get('price', 'N/A')
                    duration = flight.get('total_duration', 0)
                    layovers = len(flight.get('layovers', []))
                    
                    # Convert duration to hours and minutes
                    hours = duration // 60
                    minutes = duration % 60
                    
                    stops = 'nonstop' if layovers == 0 else f'{layovers} stop(s)'
                    print(f'   {i}. {price} - {hours}h {minutes}m ({stops})')
                    
                    # Show routing for first flight
                    if i == 1 and 'flights' in flight:
                        print(f'      Routing:')
                        for segment in flight['flights']:
                            dep = segment.get('departure_airport', {}).get('id', 'N/A')
                            arr = segment.get('arrival_airport', {}).get('id', 'N/A') 
                            airline = segment.get('airline', 'N/A')
                            flight_num = segment.get('flight_number', 'N/A')
                            dep_time = segment.get('departure_time', 'N/A')
                            arr_time = segment.get('arrival_time', 'N/A')
                            print(f'        {airline} {flight_num}: {dep} → {arr} ({dep_time} - {arr_time})')
                print()
            
            # Display other flights
            other_flights = flight_data.get('other_flights', [])
            if other_flights:
                print('✈️ OTHER FLIGHT OPTIONS:')
                for i, flight in enumerate(other_flights[:5], 1):  # Show first 5
                    price = flight.get('price', 'N/A')
                    duration = flight.get('total_duration', 0)
                    layovers = len(flight.get('layovers', []))
                    
                    hours = duration // 60
                    minutes = duration % 60
                    
                    stops = 'nonstop' if layovers == 0 else f'{layovers} stop(s)'
                    print(f'   {i}. {price} - {hours}h {minutes}m ({stops})')
                print()
            
            # Summary
            total_flights = len(best_flights) + len(other_flights)
            print(f'📊 SUMMARY:')
            print(f'   Total flights found: {total_flights}')
            print(f'   Best options: {len(best_flights)}')
            print(f'   Other options: {len(other_flights)}')
            
            if best_flights:
                cheapest = min(best_flights + other_flights, key=lambda x: int(x.get('price', '999999').replace('$', '').replace(',', '')))
                cheapest_price = cheapest.get('price', 'N/A')
                print(f'   Cheapest: {cheapest_price}')
            
        else:
            print(f"❌ Search failed: {results.get('error', 'Unknown error')}")
            print(f"Source: {results.get('source', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ Error displaying flights: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    display_pom_cdg_flights()
