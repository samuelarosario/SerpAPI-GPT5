#!/usr/bin/env python3
"""
Flight Search: CDG → POM on October 10, 2025
"""

import sys
sys.path.append('Main')
from enhanced_flight_search import EnhancedFlightSearchClient

def search_cdg_to_pom():
    """Search for flights from Paris CDG to Port Moresby on October 10th"""
    
    print('🛫 Initiating Flight Search: CDG → POM')
    print('Date: October 10, 2025')
    print('Passengers: 1 adult')
    print('Using: EnhancedFlightSearchClient.search_flights()')
    print('=' * 50)
    
    client = EnhancedFlightSearchClient()
    
    try:
        results = client.search_flights(
            departure_id='CDG',
            arrival_id='POM', 
            outbound_date='2025-10-10',
            adults=1
        )
        
        if results['success']:
            print(f'✅ Search completed successfully!')
            print(f'Source: {results["source"].upper()}')
            
            if 'data' in results:
                data = results['data']
                best_flights = data.get('best_flights', [])
                other_flights = data.get('other_flights', [])
                total_flights = len(best_flights) + len(other_flights)
                
                print(f'Found {total_flights} flight options')
                print(f'  - Best flights: {len(best_flights)}')
                print(f'  - Other flights: {len(other_flights)}')
                
                if total_flights > 0:
                    print()
                    print('⭐ Flight Options Summary:')
                    
                    # Show best flights
                    for i, flight in enumerate(best_flights[:3], 1):
                        price = flight.get('price', 'N/A')
                        duration = flight.get('total_duration', 0)
                        layovers = len(flight.get('layovers', []))
                        
                        hours = duration // 60 if duration else 0
                        minutes = duration % 60 if duration else 0
                        stops = 'nonstop' if layovers == 0 else f'{layovers} stop(s)'
                        
                        print(f'   {i}. {price} - {hours}h {minutes}m ({stops}) [BEST]')
                    
                    # Show a few other flights
                    for i, flight in enumerate(other_flights[:2], len(best_flights)+1):
                        price = flight.get('price', 'N/A')
                        duration = flight.get('total_duration', 0)
                        layovers = len(flight.get('layovers', []))
                        
                        hours = duration // 60 if duration else 0
                        minutes = duration % 60 if duration else 0
                        stops = 'nonstop' if layovers == 0 else f'{layovers} stop(s)'
                        
                        print(f'   {i}. {price} - {hours}h {minutes}m ({stops})')
                    
                    print()
                    print('🗄️ Flight data stored in database for caching')
                    print('💡 Reverse route (CDG → POM) search successful!')
                    
                else:
                    print('⚠️ No flights available for this route/date combination')
                    print('This may be due to:')
                    print('  - Limited availability on this specific date')
                    print('  - Complex routing requirements for CDG → POM')
                    print('  - API response variations')
            else:
                print('✅ Search executed - data stored in database')
                
        else:
            print(f'❌ Search failed: {results.get("error", "Unknown error")}')
            print(f'Source: {results.get("source", "Unknown")}')
            
    except Exception as e:
        print(f'❌ Search error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    search_cdg_to_pom()
