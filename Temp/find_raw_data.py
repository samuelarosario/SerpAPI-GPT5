"""
Search for raw API response data in the database
"""
import sqlite3
import json

def find_raw_api_data():
    """Search for raw API response data"""
    print("📋 CHECKING ALL POSSIBLE LOCATIONS FOR RAW API DATA")
    print("=" * 55)
    
    with sqlite3.connect("../DB/Main_DB.db") as conn:
        cursor = conn.cursor()
        
        # Check all tables for potential raw data storage
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("🔍 Searching all tables for raw response data...")
        
        for table in tables:
            # Get table structure
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Look for columns that might contain raw data
            raw_columns = [col for col in columns if 'raw' in col.lower() or 'response' in col.lower() or 'json' in col.lower()]
            
            if raw_columns:
                print(f"\n📊 {table.upper()} - potential raw data columns: {raw_columns}")
                
                for col in raw_columns:
                    cursor.execute(f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL LIMIT 1")
                    result = cursor.fetchone()
                    if result and result[0]:
                        data_sample = str(result[0])[:200] + "..." if len(str(result[0])) > 200 else str(result[0])
                        print(f"   {col}: {data_sample}")
        
        # Check if we can reconstruct the response from stored flight data
        print("\n🔧 RECONSTRUCTING API RESPONSE FROM STORED DATA:")
        
        # Get the latest search with all related data
        cursor.execute("""
        SELECT fs.search_id, fs.departure_airport_code, fs.arrival_airport_code, 
               fs.outbound_date, fs.return_date, fs.total_results
        FROM flight_searches fs 
        ORDER BY fs.created_at DESC 
        LIMIT 1
        """)
        
        search = cursor.fetchone()
        if search:
            search_id = search[0]
            print(f"\n✈️  LATEST SEARCH: {search_id}")
            print(f"   Route: {search[1]} → {search[2]}")
            print(f"   Date: {search[3]} (return: {search[4]})")
            print(f"   Total results: {search[5]}")
            
            # Get all flight results for this search
            cursor.execute("""
            SELECT fr.*, GROUP_CONCAT(fs.departure_airport_code || '-' || fs.arrival_airport_code, '|') as route
            FROM flight_results fr
            LEFT JOIN flight_segments fs ON fr.id = fs.flight_result_id
            WHERE fr.search_id = ?
            GROUP BY fr.id
            ORDER BY fr.result_rank
            """, (search_id,))
            
            flights = cursor.fetchall()
            
            print(f"\n🛫 FLIGHT RESULTS ({len(flights)} found):")
            for i, flight in enumerate(flights, 1):
                price = flight[5]  # total_price
                currency = flight[6]  # price_currency
                duration = flight[4]  # total_duration
                route = flight[-1]  # constructed route
                
                print(f"   {i}. {currency} {price} - {duration} min - Route: {route}")
            
            # Get detailed segment information
            print(f"\n📋 DETAILED FLIGHT SEGMENTS:")
            cursor.execute("""
            SELECT fs.departure_airport_code, da.airport_name,
                   fs.arrival_airport_code, aa.airport_name,
                   fs.departure_time, fs.arrival_time,
                   fs.airline_code, al.airline_name,
                   fs.flight_number, fr.total_price, fr.price_currency
            FROM flight_segments fs
            JOIN flight_results fr ON fs.flight_result_id = fr.id
            LEFT JOIN airports da ON fs.departure_airport_code = da.airport_code
            LEFT JOIN airports aa ON fs.arrival_airport_code = aa.airport_code  
            LEFT JOIN airlines al ON fs.airline_code = al.airline_code
            WHERE fr.search_id = ?
            ORDER BY fr.result_rank, fs.segment_order
            """, (search_id,))
            
            segments = cursor.fetchall()
            
            current_flight = None
            for segment in segments:
                dep_code, dep_name, arr_code, arr_name = segment[0], segment[1], segment[2], segment[3]
                dep_time, arr_time = segment[4], segment[5]
                airline_code, airline_name = segment[6], segment[7]
                flight_num, price, currency = segment[8], segment[9], segment[10]
                
                print(f"   {dep_code} ({dep_name or 'Unknown'}) → {arr_code} ({arr_name or 'Unknown'})")
                print(f"   {dep_time} → {arr_time}")
                print(f"   {airline_name or airline_code} {flight_num} - {currency} {price}")
                print()

if __name__ == "__main__":
    find_raw_api_data()
