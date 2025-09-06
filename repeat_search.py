#!/usr/bin/env python3
"""
Repeat Flight Search: CDG → POM on October 10, 2025
This should demonstrate cache functionality
"""

import sys
sys.path.append('Main')
from enhanced_flight_search import EnhancedFlightSearchClient

def repeat_search_cdg_to_pom():
    """Repeat the same search to demonstrate caching"""
    
    print('🔄 Repeating Flight Search: CDG → POM')
    print('Date: October 10, 2025')
    print('Passengers: 1 adult')
    print('Expected: Should use CACHE (not API)')
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
            print(f'Source: {results["source"].upper()} ⭐')
            
            if results['source'] == 'cache':
                cache_age = results.get('cache_age_hours', 0)
                print(f'📅 Cache Age: {cache_age:.2f} hours old')
                print('💡 Using cached data - NO API call made!')
            elif results['source'] == 'api':
                print('⚠️ Made new API call (unexpected for repeat search)')
            
            if 'data' in results:
                data = results['data']
                best_flights = data.get('best_flights', [])
                other_flights = data.get('other_flights', [])
                total_flights = len(best_flights) + len(other_flights)
                
                print(f'Found {total_flights} flight options (from {results["source"]})')
                print(f'  - Best flights: {len(best_flights)}')
                print(f'  - Other flights: {len(other_flights)}')
                
                if total_flights > 0:
                    print()
                    print('⭐ Cached Flight Results:')
                    
                    # Show best flights
                    for i, flight in enumerate(best_flights[:3], 1):
                        price = flight.get('price', 'N/A')
                        duration = flight.get('total_duration', 0)
                        layovers = len(flight.get('layovers', []))
                        
                        hours = duration // 60 if duration else 0
                        minutes = duration % 60 if duration else 0
                        stops = 'nonstop' if layovers == 0 else f'{layovers} stop(s)'
                        
                        print(f'   {i}. {price} - {hours}h {minutes}m ({stops}) [BEST]')
                    
                    if len(other_flights) > 0:
                        print(f'   ... plus {len(other_flights)} other options')
                    
                    print()
                    if results['source'] == 'cache':
                        print('🚀 CACHE PERFORMANCE: Instant results!')
                        print('💰 API COST SAVINGS: No additional API charges')
                        print('🔄 SMART CACHING: 24-hour fresh data policy')
                    
                else:
                    print('⚠️ No flights in results')
            else:
                print('✅ Search executed')
                
        else:
            print(f'❌ Search failed: {results.get("error", "Unknown error")}')
            print(f'Source: {results.get("source", "Unknown")}')
            
    except Exception as e:
        print(f'❌ Search error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    repeat_search_cdg_to_pom()
