#!/usr/bin/env python3
"""
Command-line flight search utility
Usage: python flight_search.py <departure> <arrival> <date>
Example: python flight_search.py POM CDG 2025-10-10
"""

import sys
import os
from datetime import datetime

# Add Main directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'Main'))

from enhanced_flight_search import EnhancedFlightSearchClient

def parse_date(date_str):
    """Parse date string in various formats"""
    formats = ['%Y-%m-%d', '%m-%d', '%m/%d', '%m/%d/%Y', '%Y/%m/%d']
    
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            # If year not provided, assume current year
            if fmt in ['%m-%d', '%m/%d']:
                parsed_date = parsed_date.replace(year=datetime.now().year)
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # Try parsing "Oct 10" format
    try:
        # Add current year if not provided
        if len(date_str.split()) == 2:
            date_str += f" {datetime.now().year}"
        parsed_date = datetime.strptime(date_str, '%b %d %Y')
        return parsed_date.strftime('%Y-%m-%d')
    except ValueError:
        pass
    
    raise ValueError(f"Could not parse date: {date_str}")

def main():
    if len(sys.argv) != 4:
        print("Usage: python flight_search.py <departure> <arrival> <date>")
        print("Examples:")
        print("  python flight_search.py POM CDG 2025-10-10")
        print("  python flight_search.py POM CDG 'Oct 10'")
        print("  python flight_search.py CDG POM 10-15")
        sys.exit(1)
    
    departure = sys.argv[1].upper()
    arrival = sys.argv[2].upper()
    date_input = sys.argv[3]
    
    try:
        # Parse the date
        formatted_date = parse_date(date_input)
        
        print(f'🛫 FLIGHT SEARCH: {departure} → {arrival} ({formatted_date})')
        print('=' * 60)
        
        # Initialize client and search (following MD documentation requirements)
        client = EnhancedFlightSearchClient()
        results = client.search_flights(departure, arrival, formatted_date)
        
        if results and results.get('success', False):
            # Show EFS standard format
            print(f'✅ Success: {results.get("success")}')
            print(f'📂 Source: {results.get("source")}')
            cache_age = results.get('cache_age_hours', 0)
            print(f'⏰ Cache Age: {cache_age:.4f} hours')
            
            data = results.get('data', {})
            best_flights = data.get('best_flights', [])
            other_flights = data.get('other_flights', [])
            
            total = len(best_flights) + len(other_flights)
            print(f'📊 Results: {len(best_flights)} best + {len(other_flights)} other = {total} flights')
            
            if best_flights:
                print(f'\n⭐ BEST FLIGHTS ({len(best_flights)}):')
                for i, flight in enumerate(best_flights[:5], 1):
                    price = flight.get('price', 'N/A')
                    duration = flight.get('total_duration', 'N/A')
                    stops = len(flight.get('flights', [])) - 1
                    stops_text = f'{stops} stop(s)' if stops > 0 else 'nonstop'
                    
                    print(f'  {i}. {price} - {duration} ({stops_text})')
                    
                    # Show routing for connecting flights
                    flights_list = flight.get('flights', [])
                    if len(flights_list) > 1:
                        routing = []
                        for segment in flights_list:
                            airline = segment.get('airline', 'XX')
                            flight_num = segment.get('flight_number', '000')
                            dep_airport = segment.get('departure_airport', {}).get('id', 'XXX')
                            arr_airport = segment.get('arrival_airport', {}).get('id', 'XXX')
                            routing.append(f'{airline} {flight_num}: {dep_airport} → {arr_airport}')
                        print(f'     Routing: {" | ".join(routing)}')
            
            if other_flights:
                print(f'\n🔄 OTHER OPTIONS ({len(other_flights)}):')
                for i, flight in enumerate(other_flights[:3], 1):
                    price = flight.get('price', 'N/A')
                    duration = flight.get('total_duration', 'N/A')
                    stops = len(flight.get('flights', [])) - 1
                    stops_text = f'{stops} stop(s)' if stops > 0 else 'nonstop'
                    print(f'  {i}. {price} - {duration} ({stops_text})')
        
        else:
            print('❌ No flights found or search failed')
            if results:
                print(f'Success: {results.get("success", False)}')
                print(f'Source: {results.get("source", "Unknown")}')
    
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
