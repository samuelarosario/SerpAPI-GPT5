#!/usr/bin/env python3
"""
Display POM → CDG flights from database
"""

import sys
sys.path.append('DB')
from database_helper import SerpAPIDatabase

def display_pom_cdg_from_db():
    """Display POM → CDG flights directly from database"""
    
    print('🛫 POM → CDG Flight Results (from database)')
    print('=' * 60)
    
    db = SerpAPIDatabase('DB/Main_DB.db')
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Get flight search info
        cursor.execute("""
            SELECT search_id, outbound_date, total_results, created_at
            FROM flight_searches 
            WHERE departure_airport_code = 'POM' AND arrival_airport_code = 'CDG'
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        search_info = cursor.fetchone()
        if search_info:
            print(f"Search Date: {search_info[1]}")
            print(f"Results Found: {search_info[2]} flights")
            print(f"Search Time: {search_info[3]}")
            print()
        
        # Get all flight results with price ranking
        cursor.execute("""
            SELECT fr.total_price, fr.price_currency, fr.total_duration, 
                   fr.layover_count, fr.result_type, fr.id
            FROM flight_results fr
            JOIN flight_searches fs ON fr.search_id = fs.search_id
            WHERE fs.departure_airport_code = 'POM' AND fs.arrival_airport_code = 'CDG'
            ORDER BY fr.total_price ASC
        """)
        
        flights = cursor.fetchall()
        
        if flights:
            print(f"✈️ AVAILABLE FLIGHTS ({len(flights)} options):")
            print()
            
            # Separate best and other flights
            best_flights = [f for f in flights if f[4] == 'best']
            other_flights = [f for f in flights if f[4] == 'other']
            
            if best_flights:
                print("⭐ BEST FLIGHTS:")
                for i, flight in enumerate(best_flights, 1):
                    price, currency, duration, stops, flight_type, flight_id = flight
                    hours = duration // 60 if duration else 0
                    minutes = duration % 60 if duration else 0
                    stop_text = 'nonstop' if stops == 0 else f'{stops} stop(s)'
                    
                    print(f"   {i}. {price} {currency} - {hours}h {minutes}m ({stop_text})")
                    
                    # Show routing for this flight
                    cursor.execute("""
                        SELECT departure_airport_code, arrival_airport_code, 
                               airline_code, flight_number, departure_time, arrival_time
                        FROM flight_segments 
                        WHERE flight_result_id = ?
                        ORDER BY segment_order
                    """, (flight_id,))
                    
                    segments = cursor.fetchall()
                    if segments:
                        print(f"      Route:")
                        for seg in segments:
                            dep, arr, airline, flight_num, dep_time, arr_time = seg
                            print(f"        {airline} {flight_num}: {dep} → {arr} ({dep_time} - {arr_time})")
                    print()
            
            if other_flights:
                print("💼 OTHER OPTIONS:")
                for i, flight in enumerate(other_flights[:5], 1):  # Show first 5
                    price, currency, duration, stops, flight_type, flight_id = flight
                    hours = duration // 60 if duration else 0
                    minutes = duration % 60 if duration else 0
                    stop_text = 'nonstop' if stops == 0 else f'{stops} stop(s)'
                    
                    print(f"   {i}. {price} {currency} - {hours}h {minutes}m ({stop_text})")
                
                if len(other_flights) > 5:
                    print(f"   ... and {len(other_flights) - 5} more options")
                print()
            
            # Price analysis
            prices = [int(f[0]) for f in flights]
            print("💰 PRICE ANALYSIS:")
            print(f"   Cheapest: ${min(prices):,} {flights[0][1]}")
            print(f"   Most Expensive: ${max(prices):,} {flights[0][1]}")
            print(f"   Average: ${sum(prices) // len(prices):,} {flights[0][1]}")
            
            # Duration analysis
            durations = [f[2] for f in flights if f[2]]
            if durations:
                min_duration = min(durations)
                max_duration = max(durations)
                print(f"   Fastest: {min_duration // 60}h {min_duration % 60}m")
                print(f"   Longest: {max_duration // 60}h {max_duration % 60}m")
        
        else:
            print("❌ No flights found in database")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == "__main__":
    display_pom_cdg_from_db()
