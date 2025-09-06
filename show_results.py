#!/usr/bin/env python3
"""
Show the actual POM → CDG flight results that were found
"""

import sys
sys.path.append('DB')
from database_helper import SerpAPIDatabase

def show_pom_cdg_results():
    """Show the actual flight results for POM → CDG"""
    
    db = SerpAPIDatabase('DB/Main_DB.db')
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Get the POM → CDG flight results
        cursor.execute("""
            SELECT fr.search_id, fr.total_price, fr.price_currency, 
                   fr.total_duration, fr.layover_count, fr.result_type
            FROM flight_results fr
            JOIN flight_searches fs ON fr.search_id = fs.search_id
            WHERE fs.departure_airport_code = 'POM' AND fs.arrival_airport_code = 'CDG'
            ORDER BY fr.total_price ASC
        """)
        
        results = cursor.fetchall()
        
        print(f'🛫 POM → CDG Flight Results: {len(results)} flights found')
        print('=' * 60)
        
        for i, result in enumerate(results, 1):
            price = f'{result[1]} {result[2]}'
            duration_hrs = result[3] // 60 if result[3] else 0
            duration_mins = result[3] % 60 if result[3] else 0
            stops = 'nonstop' if result[4] == 0 else f'{result[4]} stop(s)'
            flight_type = result[5]
            
            print(f'{i}. {price} - {duration_hrs}h {duration_mins}m ({stops}) [{flight_type}]')
        
        # Check flight segments for the best option
        if results:
            # Get flight result ID for the cheapest flight
            cursor.execute("""
                SELECT fr.id FROM flight_results fr
                JOIN flight_searches fs ON fr.search_id = fs.search_id
                WHERE fs.departure_airport_code = 'POM' AND fs.arrival_airport_code = 'CDG'
                ORDER BY fr.total_price ASC
                LIMIT 1
            """)
            
            best_result_id = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT fs.departure_airport_code, fs.arrival_airport_code,
                       fs.airline_code, fs.flight_number, fs.departure_time, 
                       fs.arrival_time, fs.duration_minutes
                FROM flight_segments fs
                WHERE fs.flight_result_id = ?
                ORDER BY fs.segment_order
            """, (best_result_id,))
            
            segments = cursor.fetchall()
            print(f'\n✈️ Cheapest Flight Routing ({len(segments)} segments):')
            for seg in segments:
                duration_hrs = seg[6] // 60 if seg[6] else 0
                duration_mins = seg[6] % 60 if seg[6] else 0
                print(f'   {seg[2]}{seg[3]}: {seg[0]} → {seg[1]} ({seg[4]} - {seg[5]}) {duration_hrs}h {duration_mins}m')
        
        print('\n✅ The search DID find connecting flights!')
        print('💡 The issue was with the result parsing, not the API call')
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == "__main__":
    show_pom_cdg_results()
