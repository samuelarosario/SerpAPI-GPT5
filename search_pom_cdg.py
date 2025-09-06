#!/usr/bin/env python3
"""
Flight Search: POM → CDG on October 10, 2025
"""

import sys
sys.path.append('Main')
from enhanced_flight_search import EnhancedFlightSearchClient

def search_pom_to_cdg():
    """Search for flights from Port Moresby to Paris CDG on October 10th"""
    
    # Initialize the enhanced flight search client
    client = EnhancedFlightSearchClient()
    
    # Search parameters
    departure_id = 'POM'
    arrival_id = 'CDG'
    outbound_date = '2025-10-10'
    adults = 1
    
    print('🛫 Initiating Flight Search...')
    print(f'Route: {departure_id} → {arrival_id}')
    print(f'Date: {outbound_date}')
    print(f'Passengers: {adults} adult(s)')
    print('=' * 50)
    
    try:
        # Execute the flight search
        results = client.search_flights(
            departure_id=departure_id,
            arrival_id=arrival_id,
            outbound_date=outbound_date,
            adults=adults
        )
        
        print(f'✅ Flight search completed successfully!')
        
        # Check if we have flights in the results
        flights = results.get('flights', [])
        print(f'Found {len(flights)} flight options')
        
        # Display results summary
        if flights:
            print('\n📋 Flight Options Summary:')
            for i, flight in enumerate(flights[:5], 1):
                price = flight.get('price', 'N/A')
                duration = flight.get('total_duration', 'N/A')
                layovers = flight.get('layovers', 0)
                stop_text = 'nonstop' if layovers == 0 else f'{layovers} stop(s)'
                
                # Convert duration to hours and minutes if it's in minutes
                if isinstance(duration, int):
                    hours = duration // 60
                    minutes = duration % 60
                    duration_str = f'{hours}h {minutes}m'
                else:
                    duration_str = str(duration)
                
                print(f'   {i}. {price} - {duration_str} ({stop_text})')
            
            # Show best flight details
            best_flight = flights[0]
            print(f'\n⭐ Best Flight Option:')
            print(f'   Price: {best_flight.get("price", "N/A")}')
            print(f'   Duration: {duration_str}')
            print(f'   Layovers: {best_flight.get("layovers", 0)}')
            
            # Show airline information if available
            if 'segments' in best_flight and best_flight['segments']:
                first_segment = best_flight['segments'][0]
                airline = first_segment.get('airline', 'N/A')
                print(f'   Primary Airline: {airline}')
        
        else:
            print('\n⚠️ No flights found for this route and date')
            print('This might be due to:')
            print('   - Limited routes between POM and CDG')
            print('   - Date availability issues')
            print('   - API response format differences')
        
        print('\n🗄️ Search results stored in database for future cache lookups')
        print('💡 Subsequent identical searches will use cached data')
        
    except Exception as e:
        print(f'❌ Flight search failed: {e}')
        print('Error details:')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    search_pom_to_cdg()
