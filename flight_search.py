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

def display_single_date_results(results):
    """Display results for single date search"""
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

def display_week_range_results(results):
    """Display results for week range search"""
    if results and results.get('success', False):
        summary = results.get('summary', {})
        price_trend = results.get('price_trend', {})
        
        print(f'✅ Week Search Success: {results.get("success")}')
        print(f'📅 Date Range: {results.get("date_range")}')
        print(f'📊 Search Summary: {summary.get("successful_searches", 0)}/7 days successful')
        print(f'🛫 Total Flights Found: {summary.get("total_flights_found", 0)}')
        print(f'📈 Avg Flights/Day: {summary.get("avg_flights_per_day", 0)}')
        
        # Show best deals across the week
        best_week_flights = results.get('best_week_flights', [])
        if best_week_flights:
            print(f'\n🏆 TOP 5 DEALS ACROSS THE WEEK:')
            for i, flight in enumerate(best_week_flights[:5], 1):
                price = flight.get('price', 'N/A')
                duration = flight.get('total_duration', 'N/A')
                search_date = flight.get('search_date', 'N/A')
                day_name = flight.get('day_name', 'N/A')
                stops = len(flight.get('flights', [])) - 1
                stops_text = f'{stops} stop(s)' if stops > 0 else 'nonstop'
                is_best = '⭐' if flight.get('is_best', False) else '🔄'
                
                print(f'  {i}. {price} on {search_date} ({day_name}) {is_best}')
                print(f'     Duration: {duration} ({stops_text})')
        
        # Show price trend analysis
        weekday_analysis = price_trend.get('weekday_vs_weekend', {})
        if weekday_analysis:
            print(f'\n📈 PRICE TREND ANALYSIS:')
            weekday_avg = weekday_analysis.get('weekday_avg_price', 0)
            weekend_avg = weekday_analysis.get('weekend_avg_price', 0)
            premium = weekday_analysis.get('weekend_premium', 0)
            premium_pct = weekday_analysis.get('weekend_premium_percent', 0)
            
            print(f'  💼 Weekday Average: {weekday_avg} USD')
            print(f'  🏖️  Weekend Average: {weekend_avg} USD')
            if premium > 0:
                print(f'  💰 Weekend Premium: +{premium} USD (+{premium_pct}%)')
            elif premium < 0:
                print(f'  💰 Weekend Discount: {premium} USD ({premium_pct}%)')
        
        # Show cheapest vs most expensive day
        cheapest = summary.get('cheapest_day')
        most_expensive = summary.get('most_expensive_day')
        if cheapest and most_expensive:
            print(f'\n🎯 BEST vs WORST DAYS:')
            print(f'  💚 Cheapest: {cheapest["date"]} - {cheapest["price"]} USD')
            print(f'  💸 Most Expensive: {most_expensive["date"]} - {most_expensive["price"]} USD')
            savings = most_expensive["price"] - cheapest["price"]
            print(f'  💡 Potential Savings: {savings:.0f} USD by choosing best day')
        
        # Show daily breakdown summary
        daily_min_prices = price_trend.get('daily_min_prices', {})
        if daily_min_prices:
            print(f'\n📅 DAILY PRICE SUMMARY:')
            for date_str in sorted(daily_min_prices.keys()):
                day_data = results['daily_results'].get(date_str, {})
                day_name = day_data.get('day_name', 'Unknown')
                min_price = daily_min_prices[date_str]
                flight_count = price_trend.get('daily_flight_counts', {}).get(date_str, 0)
                print(f'  {date_str} ({day_name}): {min_price:.0f} USD min, {flight_count} flights')
        
        # Show warnings if any days failed
        if summary.get('failed_searches', 0) > 0:
            print(f'\n⚠️  WARNING: {summary["failed_searches"]} days had no results')
    
    else:
        print('❌ Week range search failed')
        if results:
            print(f'Error: {results.get("error", "Unknown error")}')

def main():
    # Check for week range flag
    week_range = False
    args = sys.argv[1:]
    
    if '--week' in args or '-w' in args:
        week_range = True
        args = [arg for arg in args if arg not in ['--week', '-w']]
    
    if len(args) != 3:
        print("Usage: python flight_search.py <departure> <arrival> <date> [--week]")
        print("Examples:")
        print("  python flight_search.py POM CDG 2025-10-10")
        print("  python flight_search.py POM CDG 'Oct 10'")
        print("  python flight_search.py CDG POM 10-15")
        print("  python flight_search.py POM CDG 'Oct 10' --week  # Search 7 days starting Oct 10")
        print("  python flight_search.py POM CDG 2025-10-10 -w   # Short flag for week search")
        sys.exit(1)
    
    departure = args[0].upper()
    arrival = args[1].upper()
    date_input = args[2]
    
    try:
        # Parse the date
        formatted_date = parse_date(date_input)
        
        if week_range:
            print(f'�️ WEEK RANGE SEARCH: {departure} → {arrival} (7 days from {formatted_date})')
            print('=' * 70)
        else:
            print(f'�🛫 FLIGHT SEARCH: {departure} → {arrival} ({formatted_date})')
            print('=' * 60)
        
        # Initialize client and search
        client = EnhancedFlightSearchClient()
        
        if week_range:
            results = client.search_week_range(departure, arrival, formatted_date)
            display_week_range_results(results)
        else:
            results = client.search_flights(departure, arrival, formatted_date)
            display_single_date_results(results)
    
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
