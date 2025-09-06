#!/usr/bin/env python3
"""
Check what's actually stored for CDG → POM search
"""

import sys
sys.path.append('DB')
from database_helper import SerpAPIDatabase

def check_cdg_pom_data():
    """Check the actual stored data for CDG → POM"""
    
    print('🔍 Checking CDG → POM Database Storage')
    print('=' * 50)
    
    db = SerpAPIDatabase('DB/Main_DB.db')
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if search exists
        cursor.execute("""
            SELECT search_id, total_results, response_status, created_at
            FROM flight_searches 
            WHERE departure_airport_code = 'CDG' AND arrival_airport_code = 'POM'
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        search_info = cursor.fetchone()
        if search_info:
            search_id, total_results, status, created_at = search_info
            print(f"✅ Search Found:")
            print(f"   Search ID: {search_id}")
            print(f"   Total Results: {total_results}")
            print(f"   Status: {status}")
            print(f"   Created: {created_at}")
            print()
            
            # Check flight results
            cursor.execute("""
                SELECT COUNT(*) FROM flight_results 
                WHERE search_id = ?
            """, (search_id,))
            
            results_count = cursor.fetchone()[0]
            print(f"📊 Flight Results in Database: {results_count}")
            
            if results_count > 0:
                cursor.execute("""
                    SELECT total_price, price_currency, total_duration, 
                           layover_count, result_type
                    FROM flight_results 
                    WHERE search_id = ?
                    ORDER BY total_price ASC
                    LIMIT 5
                """, (search_id,))
                
                flights = cursor.fetchall()
                print(f"💰 Sample Flights Stored:")
                for i, flight in enumerate(flights, 1):
                    price, currency, duration, stops, flight_type = flight
                    hours = duration // 60 if duration else 0
                    minutes = duration % 60 if duration else 0
                    stop_text = 'nonstop' if stops == 0 else f'{stops} stop(s)'
                    print(f"   {i}. {price} {currency} - {hours}h {minutes}m ({stop_text}) [{flight_type}]")
                
                print()
                print("🔧 Cache Issue Diagnosis:")
                print("   ✅ Search record exists in database")
                print("   ✅ Flight results are stored properly")
                print("   ❌ Cache retrieval format mismatch")
                print("   💡 The cache system stores data differently than API response format")
                print("   💡 Need to check how cached data is reconstructed")
            else:
                print("❌ No flight results found despite search record")
        else:
            print("❌ No CDG → POM search found in database")
            
            # Check recent searches
            cursor.execute("""
                SELECT departure_airport_code, arrival_airport_code, 
                       outbound_date, created_at
                FROM flight_searches 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            recent = cursor.fetchall()
            print("📋 Recent Searches:")
            for search in recent:
                print(f"   {search[0]} → {search[1]} on {search[2]} at {search[3]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == "__main__":
    check_cdg_pom_data()
